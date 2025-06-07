# FastAPI server code
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..retriever import get_answer
import yaml
import os

app = FastAPI(title="RAG LLM API Pipeline")

CONFIG_PATH = "config/system.yaml"


class QueryRequest(BaseModel):
    system: str
    question: str


def load_system_config(system_name: str) -> list[str]:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    for asset in config.get("assets", []):
        if asset["name"].lower() == system_name.lower():
            return asset.get("docs", [])
    raise ValueError(f"System '{system_name}' not found in config.")


@app.post("/query")
def query_system(request: QueryRequest):
    try:
        _ = load_system_config(request.system)
        answer, sources = get_answer(request.system, request.question)
        return {
            "system": request.system,
            "question": request.question,
            "answer": answer,
            "sources": sources,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
