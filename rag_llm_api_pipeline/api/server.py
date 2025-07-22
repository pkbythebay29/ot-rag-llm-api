"""
FastAPI server for RAG LLM API Pipeline
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_llm_api_pipeline.retriever import get_answer
import logging

app = FastAPI(title="RAG LLM API Pipeline")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class QueryRequest(BaseModel):
    system: str
    question: str

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.post("/query", tags=["Query"])
def query_system(request: QueryRequest):
    """
    Run a RAG query for a specific system and question.
    """
    try:
        logger.info(f"Received query: system={request.system} question={request.question}")
        answer, sources = get_answer(request.system, request.question)
        return {
            "system": request.system,
            "question": request.question,
            "answer": answer,
            "sources": sources,
        }
    except Exception as e:
        logger.error(f"Error handling query: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Optional: serve webapp if directory exists
if os.path.isdir("webapp"):
    app.mount("/", StaticFiles(directory="webapp", html=True), name="web")

def start_api_server():
    import uvicorn
    uvicorn.run("rag_llm_api_pipeline.api.server:app", host="0.0.0.0", port=8000, reload=True)
