"""
FastAPI server for RAG LLM API Pipeline
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import logging

from rag_llm_api_pipeline.retriever import get_answer

# --- FastAPI App ---
app = FastAPI(title="RAG LLM API Pipeline")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Request Body Model ---
class QueryRequest(BaseModel):
    system: str
    question: str


# --- Health Check Route ---
@app.get("/health", tags=["Health"])
def health():
    logger.info("Health check called")
    return {"status": "ok"}


# --- Query Endpoint ---
@app.post("/query", tags=["Query"])
def query_system(request: QueryRequest):
    try:
        logger.info(f"Received query: system='{request.system}', question='{request.question}'")
        answer, sources = get_answer(request.system, request.question)
        return {
            "system": request.system,
            "question": request.question,
            "answer": answer,
            "sources": sources,
        }
    except Exception as e:
        logger.exception("Error processing query")
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- Serve Webapp (from working dir) ---
WORKING_WEBAPP_DIR = os.path.abspath(os.path.join(os.getcwd(), "webapp"))
if os.path.isdir(WORKING_WEBAPP_DIR):
    logger.info(f"Mounting webapp from: {WORKING_WEBAPP_DIR}")
    app.mount("/", StaticFiles(directory=WORKING_WEBAPP_DIR, html=True), name="web")
else:
    logger.warning(f"webapp directory not found at: {WORKING_WEBAPP_DIR}")


# --- Run Uvicorn Programmatically (Optional) ---
def start_api_server():
    import uvicorn
    uvicorn.run("rag_llm_api_pipeline.api.server:app", host="0.0.0.0", port=8000, reload=True)
