# Interface to local LLM

from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from .config_loader import load_config

config = load_config()
MODEL_NAME = config["models"]["llm_model"]

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
device = -1 if config["settings"].get("use_cpu", True) else 0
llm = pipeline("text-generation", model=model, tokenizer=tokenizer, device=device)

def format_prompt(question: str, context: str) -> str:
    return config["llm"]["prompt_template"].format(question=question, context=context)

def ask_llm(question: str, context: str) -> str:
    prompt = format_prompt(question, context)
    output = llm(prompt, max_new_tokens=config["llm"]["max_new_tokens"], do_sample=False)
    return output[0]["generated_text"].split("Answer:")[-1].strip()
