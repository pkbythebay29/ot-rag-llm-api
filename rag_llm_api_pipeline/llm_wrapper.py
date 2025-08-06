import os
import gc
import yaml
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

def load_yaml_config(path="config/system.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_llm():
    config = load_yaml_config()
    model_name = config["models"]["llm_model"]
    device_preference = config["models"].get("device", "auto")
    precision = config["models"].get("model_precision", "auto")
    memory_conf = config["models"].get("memory_strategy", {})
    max_memory_gb = memory_conf.get("max_memory_gb")
    use_expandable_segments = memory_conf.get("use_expandable_segments", True)

    # Device handling
    if device_preference == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = device_preference

    # Precision
    dtype_map = {
        "fp16": torch.float16,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "fp32": torch.float32,
        "float32": torch.float32,
        "auto": torch.float16 if device == "cuda" else torch.float32
    }
    torch_dtype = dtype_map.get(precision.lower(), torch.float32)

    # Prevent GPU fragmentation
    if device == "cuda" and use_expandable_segments:
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    # Clear previous memory if any
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if device == "cuda":
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map={"": 0}  # avoid "auto" sharding which overallocates
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch_dtype
        )

    return pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device=0 if device == "cuda" else -1
    )

def ask_llm(question: str, context: str) -> str:
    config = load_yaml_config()
    template = config["llm"]["prompt_template"]
    prompt = template.replace("{context}", context).replace("{question}", question)
    max_tokens = config["llm"].get("max_new_tokens", 256)

    pipe = load_llm()
    response = pipe(prompt, max_new_tokens=max_tokens)[0]["generated_text"]
    return response.replace(prompt, "").strip()
