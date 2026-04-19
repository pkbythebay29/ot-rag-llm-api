from __future__ import annotations

import gc
import os
import time
from typing import Any

from rag_llm_api_pipeline.config_loader import get_config_path, load_config
from rag_llm_api_pipeline.core.model_selection import resolve_runtime_selection

_RUNTIME_CACHE: dict[str, dict[str, Any]] = {}


def _torch():
    import torch

    return torch


def _transformers():
    from transformers import (  # type: ignore
        AutoModelForCausalLM,
        AutoTokenizer,
        StoppingCriteria,
        StoppingCriteriaList,
        pipeline,
    )

    return {
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "StoppingCriteria": StoppingCriteria,
        "StoppingCriteriaList": StoppingCriteriaList,
        "pipeline": pipeline,
    }


def _quantize_dynamic():
    try:
        from torch.ao.quantization import quantize_dynamic
    except ImportError:  # pragma: no cover - compatibility fallback
        from torch.quantization import quantize_dynamic

    return quantize_dynamic


def _select_device(runtime: dict[str, Any]) -> str:
    torch = _torch()
    prefer = runtime.get("device", "auto")
    if runtime.get("use_cpu", False):
        return "cpu"
    if prefer == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cuda" if (prefer == "cuda" and torch.cuda.is_available()) else "cpu"


def _select_dtype(runtime: dict[str, Any], llm_cfg: dict[str, Any], device: str):
    torch = _torch()
    precision = (
        runtime.get("model_precision") or llm_cfg.get("precision") or "auto"
    ).lower()
    if precision in ("fp16", "float16"):
        return torch.float16
    if precision in ("bf16", "bfloat16"):
        return torch.bfloat16
    if precision in ("fp32", "float32"):
        return torch.float32
    return torch.float16 if device == "cuda" else torch.float32


def _select_quantization_backend(runtime: dict[str, Any], device: str) -> str:
    backend = str(runtime.get("quantization_backend", "auto")).strip().lower()
    if backend in {"", "none", "off", "false", "disabled"}:
        return "none"
    if backend == "auto":
        return "dynamic-int8" if device == "cpu" else "none"
    if device == "cuda":
        return "none"
    return backend


def _build_model_load_kwargs(
    runtime: dict[str, Any], device: str, dtype: Any, quant_backend: str
) -> dict[str, Any]:
    torch = _torch()
    kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "low_cpu_mem_usage": bool(runtime.get("low_cpu_mem_usage", True)),
    }
    if device == "cuda":
        kwargs["torch_dtype"] = dtype
        kwargs["device_map"] = "auto"
        return kwargs

    kwargs["device_map"] = None
    kwargs["torch_dtype"] = torch.float32 if quant_backend == "dynamic-int8" else dtype
    return kwargs


def _tok_ids(tokenizer: Any, text: str) -> list[int]:
    return tokenizer(text, add_special_tokens=False)["input_ids"]


def _ids_to_text(tokenizer: Any, ids: list[int]) -> str:
    return tokenizer.decode(ids, skip_special_tokens=True)


def _model_max_input(tokenizer: Any, llm_cfg: dict[str, Any]) -> int:
    model_max = getattr(tokenizer, "model_max_length", None)
    if model_max is None or model_max > 10_000_000_000_000_000:
        return int(llm_cfg.get("max_input_tokens", 3072))
    return min(int(llm_cfg.get("max_input_tokens", model_max)), int(model_max))


def _truncate_rag_prompt(
    *,
    tokenizer: Any,
    question: str,
    context: str,
    template: str,
    max_len: int,
) -> str:
    if "{question}" not in template or "{context}" not in template:
        template = (
            "You are a helpful assistant for industrial systems.\n\n"
            'Use ONLY the provided context to answer. If the answer is not in the context, say "I don\'t know."\n\n'
            "Question: {question}\n\nContext:\n{context}\n\nAnswer:"
        )
    head, tail = template.split("{context}", 1)
    head = head.format(question=question, context="")
    tail = tail.format(question=question, context="")
    head_ids = _tok_ids(tokenizer, head)
    tail_ids = _tok_ids(tokenizer, tail)
    context_ids = _tok_ids(tokenizer, context)
    budget = max_len - (len(head_ids) + len(tail_ids))
    if budget < 0:
        keep_head = max(0, max_len - len(tail_ids))
        head_ids = head_ids[-keep_head:]
        budget = max(0, max_len - (len(head_ids) + len(tail_ids)))
    if len(context_ids) > budget:
        context_ids = context_ids[-budget:] if budget > 0 else []
    return _ids_to_text(tokenizer, head_ids + context_ids + tail_ids)


def _build_gen_kwargs(llm_cfg: dict[str, Any], tokenizer: Any) -> dict[str, Any]:
    gen_kwargs = {
        "max_new_tokens": int(llm_cfg.get("max_new_tokens", 256)),
        "repetition_penalty": float(llm_cfg.get("repetition_penalty", 1.05)),
        "no_repeat_ngram_size": int(llm_cfg.get("no_repeat_ngram_size", 3)),
        "return_full_text": False,
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    preset_name = llm_cfg.get("preset", "baseline")
    preset_cfg = (llm_cfg.get("presets", {}) or {}).get(preset_name, {})
    gen_kwargs.update(preset_cfg)
    if "num_beams" in gen_kwargs:
        gen_kwargs["num_beams"] = int(gen_kwargs["num_beams"])
    if "num_return_sequences" in gen_kwargs:
        gen_kwargs["num_return_sequences"] = int(gen_kwargs["num_return_sequences"])
    if not gen_kwargs.get("do_sample", False):
        for key in ("temperature", "top_p", "top_k", "num_return_sequences"):
            gen_kwargs.pop(key, None)
    return gen_kwargs


def _stop_on_sequences_class():
    transformers = _transformers()
    base = transformers["StoppingCriteria"]

    class _StopOnSequences(base):
        def __init__(self, stop_strings: list[str], tokenizer: Any):
            self._stop_texts = [
                value.strip().lower()
                for value in (stop_strings or [])
                if value and value.strip()
            ]
            self._tok = tokenizer
            self._max_len = 0
            if self._stop_texts:
                self._stop_ids = [
                    tokenizer.encode(value, add_special_tokens=False)
                    for value in self._stop_texts
                ]
                self._max_len = max((len(value) for value in self._stop_ids), default=0)

        def __call__(self, input_ids, scores, **kwargs):
            if self._max_len == 0:
                return False
            for seq in input_ids:
                tail_ids = seq[-self._max_len :].tolist()
                tail_text = (
                    self._tok.decode(tail_ids, skip_special_tokens=True).strip().lower()
                )
                for stop_text in self._stop_texts:
                    if tail_text.endswith(stop_text):
                        return True
            return False

    return _StopOnSequences


def _maybe_add_stopping_criteria(
    gen_kwargs: dict[str, Any], llm_cfg: dict[str, Any], tokenizer: Any
) -> dict[str, Any]:
    stop_sequences = llm_cfg.get("stop_sequences", []) or []
    if stop_sequences:
        transformers = _transformers()
        gen_kwargs["stopping_criteria"] = transformers["StoppingCriteriaList"](
            [_stop_on_sequences_class()(stop_sequences, tokenizer)]
        )
    gen_kwargs.pop("stop", None)
    return gen_kwargs


def _load_runtime(model_selection: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config()
    llm_cfg = cfg.get("llm", {}) or {}
    runtime = resolve_runtime_selection(cfg, overrides=model_selection)
    cache_key = runtime["signature"]
    cached = _RUNTIME_CACHE.get(cache_key)
    if cached is not None:
        return cached

    torch = _torch()
    transformers = _transformers()
    device = _select_device(runtime)
    dtype = _select_dtype(runtime, llm_cfg, device)
    quant_backend = _select_quantization_backend(runtime, device)

    if device == "cuda" and cfg.get("models", {}).get("memory_strategy", {}).get(
        "use_expandable_segments", True
    ):
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    model_name = runtime["inference_model"]
    tokenizer = transformers["AutoTokenizer"].from_pretrained(
        model_name, trust_remote_code=True
    )
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = transformers["AutoModelForCausalLM"].from_pretrained(
        model_name,
        **_build_model_load_kwargs(runtime, device, dtype, quant_backend),
    )

    if quant_backend == "dynamic-int8":
        model = _quantize_dynamic()(model, {torch.nn.Linear}, dtype=torch.qint8)
        model.eval()

    pipe_kwargs: dict[str, Any] = {
        "model": model,
        "tokenizer": tokenizer,
        "model_kwargs": {"torch_dtype": dtype},
    }
    if device != "cuda":
        pipe_kwargs["device"] = -1

    pipe = transformers["pipeline"]("text-generation", **pipe_kwargs)
    runtime_state = {
        "config": cfg,
        "llm_cfg": llm_cfg,
        "runtime": runtime,
        "device": device,
        "dtype": dtype,
        "quantization_backend": quant_backend,
        "tokenizer": tokenizer,
        "pipeline": pipe,
    }
    _RUNTIME_CACHE[cache_key] = runtime_state
    return runtime_state


def ask_llm(question: str, context: str, model_selection: dict[str, Any] | None = None):
    state = _load_runtime(model_selection=model_selection)
    llm_cfg = state["llm_cfg"]
    tokenizer = state["tokenizer"]
    runtime = state["runtime"]
    template = llm_cfg.get(
        "prompt_template",
        (
            "You are a helpful assistant for industrial systems.\n\n"
            'Use the provided context to answer. If the answer is not in the context, say "I don\'t know."\n\n'
            "Question: {question}\n\nContext:\n{context}\n\nAnswer:"
        ),
    )
    prompt = _truncate_rag_prompt(
        tokenizer=tokenizer,
        question=question,
        context=context,
        template=template,
        max_len=_model_max_input(tokenizer, llm_cfg),
    )
    gen_kwargs = _build_gen_kwargs(llm_cfg, tokenizer)
    gen_kwargs = _maybe_add_stopping_criteria(gen_kwargs, llm_cfg, tokenizer)

    started_at = time.perf_counter()
    out = state["pipeline"](prompt, **gen_kwargs)
    finished_at = time.perf_counter()
    text = (out[0]["generated_text"] if out else "").strip()
    gen_tokens = len(tokenizer.encode(text)) if text else 0
    gen_time = max(finished_at - started_at, 1e-9)
    stats = {
        "gen_time_sec": round(gen_time, 4),
        "gen_tokens": gen_tokens,
        "tokens_per_sec": round(gen_tokens / gen_time, 3),
        "runtime_profile": runtime.get("runtime_profile"),
        "inference_model": runtime.get("inference_model"),
        "embedding_model": runtime.get("embedding_model"),
        "device": state["device"],
        "quantization_backend": state["quantization_backend"],
    }
    return text, stats


class LLMWrapper:
    """
    Thin adapter around `ask_llm(question, context, model_selection=...)`.
    """

    def __init__(
        self,
        config_path: str | None = None,
        model_selection: dict[str, Any] | None = None,
        **kwargs,
    ):
        self.config_path = config_path or get_config_path()
        self.model_selection = dict(model_selection or {})
        self.extra = kwargs

    def _merged_selection(
        self, overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        merged = dict(self.model_selection)
        for key, value in dict(overrides or {}).items():
            if value is not None:
                merged[key] = value
        return merged

    def generate(self, question: str, context: str, **kwargs):
        model_selection = self._merged_selection(kwargs.pop("model_selection", None))
        text, stats = ask_llm(
            question=question,
            context=context,
            model_selection=model_selection,
        )
        return {"text": text, "stats": stats}

    def complete(self, question: str, context: str, **kwargs):
        return self.generate(question=question, context=context, **kwargs)

    def chat(self, messages: list[dict], **kwargs):
        question = ""
        context_parts = []
        for message in messages:
            role = (message.get("role") or "").lower()
            content = message.get("content") or ""
            if role == "user":
                question = content
            else:
                context_parts.append(f"{role}: {content}")
        return self.generate(
            question=question,
            context="\n".join(context_parts).strip(),
            **kwargs,
        )

    def __call__(self, question: str, context: str, **kwargs):
        return self.generate(question=question, context=context, **kwargs)
