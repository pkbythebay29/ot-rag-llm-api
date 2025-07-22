# Interface to local LLM

from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from rag_llm_api_pipeline.config_loader import load_config

config = load_config()
llm_config = config.get("llm", {})
model_name = config["models"]["llm_model"]

device = 0 if torch.cuda.is_available() and not config["settings"].get("use_cpu", False) else -1

# Handle precision
precision = llm_config.get("precision", "fp32").lower()
if precision == "fp16":
    torch_dtype = torch.float16
elif precision == "bfloat16":
    torch_dtype = torch.bfloat16
else:
    torch_dtype = torch.float32

print(f"Loading model: {model_name} on {'GPU' if device >=0 else 'CPU'} with precision: {precision}")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch_dtype,
    device_map="auto" if device >= 0 else None
)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device=device
)

def ask_llm(question, context):
    template = llm_config.get("prompt_template", "")
    prompt = template.format(context=context, question=question)

    max_len = getattr(model.config, "max_position_embeddings", 1024)
    tokens = tokenizer.encode(prompt)
    if len(tokens) > max_len:
        tokens = tokens[-max_len:]
    prompt = tokenizer.decode(tokens)

    max_tokens = llm_config.get("max_new_tokens", 256)
    response = pipe(prompt, max_new_tokens=max_tokens)
    return response[0]['generated_text'].strip()
