import os
import gc
import time
import yaml
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from transformers import StoppingCriteria, StoppingCriteriaList  # minimal patch import

CONFIG_PATH = "config/system.yaml"


def _load_cfg():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


_cfg = _load_cfg()
_models = _cfg.get("models", {})
_llm = _cfg.get("llm", {})
_settings = _cfg.get("settings", {})

MODEL_NAME = _models["llm_model"]


def _select_device():
    prefer = _models.get("device", "auto")
    if _settings.get("use_cpu", False):
        return "cpu"
    if prefer == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cuda" if (prefer == "cuda" and torch.cuda.is_available()) else "cpu"


def _select_dtype(device: str):
    prec = (_models.get("model_precision") or _llm.get("precision") or "auto").lower()
    if prec in ("fp16", "float16"):
        return torch.float16
    if prec in ("bf16", "bfloat16"):
        return torch.bfloat16
    if prec in ("fp32", "float32"):
        return torch.float32
    return torch.float16 if device == "cuda" else torch.float32


_device = _select_device()
_dtype = _select_dtype(_device)

# CUDA fragmentation mitigation
if _device == "cuda" and _models.get("memory_strategy", {}).get(
    "use_expandable_segments", True
):
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

gc.collect()
if _device == "cuda":
    torch.cuda.empty_cache()

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
    tokenizer.pad_token_id = tokenizer.eos_token_id

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=_dtype,
    device_map="auto" if _device == "cuda" else None,
    trust_remote_code=True,
)

# Avoid Accelerate conflict
pipe_kwargs = {
    "model": model,
    "tokenizer": tokenizer,
    "model_kwargs": {"dtype": _dtype},
}
if _device != "cuda":
    pipe_kwargs["device"] = -1

pipe = pipeline("text-generation", **pipe_kwargs)


def _tok_ids(text: str):
    return tokenizer(text, add_special_tokens=False)["input_ids"]


def _ids_to_text(ids):
    return tokenizer.decode(ids, skip_special_tokens=True)


def _model_max_input():
    m = getattr(tokenizer, "model_max_length", None)
    if m is None or m > 10_000_000_000_000_000:
        return int(_llm.get("max_input_tokens", 3072))
    return min(int(_llm.get("max_input_tokens", m)), int(m))


def _truncate_rag_prompt(
    question: str, context: str, template: str, max_len: int
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
    head_ids = _tok_ids(head)
    tail_ids = _tok_ids(tail)
    ctx_ids = _tok_ids(context)
    budget = max_len - (len(head_ids) + len(tail_ids))
    if budget < 0:
        keep_head = max(0, max_len - len(tail_ids))
        head_ids = head_ids[-keep_head:]
        budget = max(0, max_len - (len(head_ids) + len(tail_ids)))
    if len(ctx_ids) > budget:
        ctx_ids = ctx_ids[-budget:] if budget > 0 else []
    return _ids_to_text(head_ids + ctx_ids + tail_ids)


def _build_gen_kwargs(llm_cfg, tokenizer):
    g = {
        "max_new_tokens": int(llm_cfg.get("max_new_tokens", 256)),
        "repetition_penalty": float(llm_cfg.get("repetition_penalty", 1.05)),
        "no_repeat_ngram_size": int(llm_cfg.get("no_repeat_ngram_size", 3)),
        "return_full_text": False,
        "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    preset_name = llm_cfg.get("preset", "baseline")
    preset_cfg = (llm_cfg.get("presets", {}) or {}).get(preset_name, {})
    g.update(preset_cfg)
    if "num_beams" in g:
        g["num_beams"] = int(g["num_beams"])
    if "num_return_sequences" in g:
        g["num_return_sequences"] = int(g["num_return_sequences"])
    if not g.get("do_sample", False):
        for k in ("temperature", "top_p", "top_k", "num_return_sequences"):
            g.pop(k, None)
    return g


#  stopping criteria (case/whitespace-insensitive) ---
class _StopOnSequences(StoppingCriteria):
    def __init__(self, stop_strings, tokenizer):
        self._stop_texts = [
            s.strip().lower() for s in (stop_strings or []) if s and s.strip()
        ]
        self._tok = tokenizer
        self._max_len = 0
        if self._stop_texts:
            self._stop_ids = [
                tokenizer.encode(s, add_special_tokens=False) for s in self._stop_texts
            ]
            self._max_len = max((len(s) for s in self._stop_ids), default=0)

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


def _maybe_add_stopping_criteria(gen_kwargs, llm_cfg, tokenizer):
    stop = llm_cfg.get("stop_sequences", []) or []
    if stop:
        gen_kwargs["stopping_criteria"] = StoppingCriteriaList(
            [_StopOnSequences(stop, tokenizer)]
        )
    gen_kwargs.pop("stop", None)
    return gen_kwargs


# --- PATCH END ---


def ask_llm(question: str, context: str):
    template = _llm.get(
        "prompt_template",
        (
            "You are a helpful assistant for industrial systems.\n\n"
            'Use the provided context to answer. If the answer is not in the context, say "I don\'t know."\n\n'
            "Question: {question}\n\nContext:\n{context}\n\nAnswer:"
        ),
    )
    prompt = _truncate_rag_prompt(
        question, context, template, max_len=_model_max_input()
    )
    gen_kwargs = _build_gen_kwargs(_llm, tokenizer)
    gen_kwargs = _maybe_add_stopping_criteria(gen_kwargs, _llm, tokenizer)

    t0 = time.perf_counter()
    out = pipe(prompt, **gen_kwargs)
    t1 = time.perf_counter()
    text = (out[0]["generated_text"] if out else "").strip()
    gen_tokens = len(tokenizer.encode(text)) if text else 0
    gen_time = max(t1 - t0, 1e-9)
    stats = {
        "gen_time_sec": round(gen_time, 4),
        "gen_tokens": gen_tokens,
        "tokens_per_sec": round(gen_tokens / gen_time, 3),
    }
    return text, stats


# --------------------------------------------------------------------------------------
# Backward-compatibility shim so callers can `from rag_llm_api_pipeline.llm_wrapper import LLMWrapper`
# The orchestrator expects a class with a simple "generate" / "complete" interface.
# We reuse the already-initialized global pipeline & tokenizer above.
# --------------------------------------------------------------------------------------
class LLMWrapper:
    """
    Thin adapter around `ask_llm(question, context)` for backward compatibility.

    Usage patterns supported:
      - LLMWrapper().generate(question=..., context=...)
      - LLMWrapper().complete(question=..., context=...)
      - LLMWrapper()(question, context)  # callable
    """

    def __init__(self, config_path: str | None = None, **kwargs):
        # We already loaded the pipeline with module-level CONFIG_PATH.
        # If a different path is passed, we ignore it (or you can add reload logic later).
        self.config_path = config_path or CONFIG_PATH
        self.extra = kwargs

    def generate(self, question: str, context: str, **kwargs):
        text, stats = ask_llm(question=question, context=context)
        # Return a simple, common shape
        return {"text": text, "stats": stats}

    # Some callers use "complete" instead of "generate"
    def complete(self, question: str, context: str, **kwargs):
        return self.generate(question=question, context=context, **kwargs)

    # Some callers may expect a chat-like API; we support a single-turn form
    def chat(self, messages: list[dict], **kwargs):
        """
        messages: [{ "role": "user"/"system"/"assistant", "content": "..." }, ...]
        We build a (question, context) pair: last user message = question,
        earlier non-user messages concatenated as context.
        """
        q = ""
        ctx_parts = []
        for m in messages:
            role = (m.get("role") or "").lower()
            content = m.get("content") or ""
            if role == "user":
                q = content
            else:
                ctx_parts.append(f"{role}: {content}")
        context = "\n".join(ctx_parts).strip()
        return self.generate(question=q, context=context or "", **kwargs)

    # Allow callable instance: LLMWrapper()(question, context)
    def __call__(self, question: str, context: str, **kwargs):
        return self.generate(question=question, context=context, **kwargs)
