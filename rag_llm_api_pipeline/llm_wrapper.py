# rag_llm_api_pipeline/llm_wrapper.py
import os
import gc
import yaml
import time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

CONFIG_PATH = "config/system.yaml"


def _load_cfg():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _select_device(cfg):
    prefer = cfg["models"].get("device", "auto")
    force_cpu = cfg["settings"].get("use_cpu", False)
    if force_cpu:
        return "cpu", -1
    if prefer == "auto":
        if torch.cuda.is_available():
            return "cuda", 0
        return "cpu", -1
    if prefer == "cuda" and torch.cuda.is_available():
        return "cuda", 0
    return "cpu", -1


def _select_dtype(cfg, device):
    prec = cfg["models"].get("model_precision", "auto").lower()
    if prec in ("fp16", "float16"):
        return torch.float16
    if prec in ("bf16", "bfloat16"):
        return torch.bfloat16
    if prec in ("fp32", "float32"):
        return torch.float32
    return torch.float16 if device == "cuda" else torch.float32


def _maybe_set_allocator(cfg, device):
    if device == "cuda" and cfg["models"].get("memory_strategy", {}).get(
        "use_expandable_segments", True
    ):
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def _truncate_prompt(tokenizer, text, max_len):
    enc = tokenizer(text, truncation=True, max_length=max_len, return_tensors="pt")
    return tokenizer.decode(enc["input_ids"][0], skip_special_tokens=True)


def _build_pipeline(cfg):
    model_name = cfg["models"]["llm_model"]
    device, device_idx = _select_device(cfg)
    dtype = _select_dtype(cfg, device)
    _maybe_set_allocator(cfg, device)

    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    tokenizer = AutoTokenizer.from_pretrained(model_name)  # nosec B615
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(  # nosec B615
        model_name,
        torch_dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device=device_idx,
        model_kwargs={"torch_dtype": dtype},
    )
    return pipe, tokenizer


def ask_llm(question: str, context: str):
    """
    Returns: (answer_text, gen_stats_dict)
    gen_stats_dict: {
      "gen_time_sec": float, "gen_tokens": int, "tokens_per_sec": float
    }
    """
    cfg = _load_cfg()
    use_harmony = cfg["models"].get("use_harmony", False)
    pipe, tok = _build_pipeline(cfg)

    # Compose prompt & truncate to guard context window
    prompt = cfg["llm"]["prompt_template"].format(context=context, question=question)
    max_input = int(cfg["llm"].get("max_input_tokens", 3072))
    prompt = _truncate_prompt(tok, prompt, max_input)

    gen_kwargs = {
        "max_new_tokens": int(cfg["llm"].get("max_new_tokens", 256)),
        "temperature": float(cfg["llm"].get("temperature", 0.2)),
        "top_p": float(cfg["llm"].get("top_p", 0.9)),
        "repetition_penalty": float(cfg["llm"].get("repetition_penalty", 1.05)),
        "no_repeat_ngram_size": int(cfg["llm"].get("no_repeat_ngram_size", 4)),
        "return_full_text": False,
        "pad_token_id": pipe.tokenizer.pad_token_id or pipe.tokenizer.eos_token_id,
        "eos_token_id": pipe.tokenizer.eos_token_id,
    }
    stop = cfg["llm"].get("stop_sequences", [])
    if stop:
        gen_kwargs["stop"] = stop

    # Harmony path (for openai/gpt-oss family)
    if use_harmony:
        from openai_harmony import (
            load_harmony_encoding,
            HarmonyEncodingName,
            Conversation,
            Message,
            Role,
            SystemContent,
            DeveloperContent,
        )

        enc = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        convo = Conversation.from_messages(
            [
                Message.from_role_and_content(Role.SYSTEM, SystemContent.new()),
                Message.from_role_and_content(
                    Role.DEVELOPER, DeveloperContent.new().with_instructions(prompt)
                ),
                Message.from_role_and_content(Role.USER, question),
            ]
        )
        prefill_ids = enc.render_conversation_for_completion(convo, Role.ASSISTANT)

        t0 = time.perf_counter()
        with torch.no_grad():
            device = pipe.model.device
            input_ids = torch.tensor([prefill_ids], device=device)
            out = pipe.model.generate(
                input_ids=input_ids,
                **{
                    k: v
                    for k, v in gen_kwargs.items()
                    if k not in ["return_full_text", "stop"]
                },
            )
        t1 = time.perf_counter()

        completion = out[0].tolist()[len(prefill_ids) :]
        msgs = enc.parse_messages_from_completion_tokens(completion, Role.ASSISTANT)
        text = next(
            (m.content for m in reversed(msgs) if m.role == Role.ASSISTANT), ""
        ).strip()

        gen_tokens = len(tok.encode(text)) if text else 0
        gen_time = max(t1 - t0, 1e-9)
        stats = {
            "gen_time_sec": round(gen_time, 4),
            "gen_tokens": gen_tokens,
            "tokens_per_sec": round(gen_tokens / gen_time, 3),
        }
        return text, stats

    # Standard HF path
    t0 = time.perf_counter()
    result = pipe(prompt, **gen_kwargs)
    t1 = time.perf_counter()

    text = (result[0]["generated_text"] if result else "").strip()
    gen_tokens = len(tok.encode(text)) if text else 0
    gen_time = max(t1 - t0, 1e-9)
    stats = {
        "gen_time_sec": round(gen_time, 4),
        "gen_tokens": gen_tokens,
        "tokens_per_sec": round(gen_tokens / gen_time, 3),
    }
    return text, stats
