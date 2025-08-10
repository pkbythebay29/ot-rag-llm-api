"""
FastAPI server for RAG LLM API Pipeline (reconciled)
- Serves web UI (from CWD/webapp or fallbacks)
- /health and /query endpoints
- Optional stats in response (controlled via YAML)
"""

"""
FastAPI server for RAG LLM API Pipeline (always returns sources)
"""

import os
import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_llm_api_pipeline.retriever import get_answer
from rag_llm_api_pipeline.config_loader import load_config

import uvicorn

app = FastAPI(title="RAG LLM API Pipeline")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    system: str
    question: str


@app.get("/health", tags=["Health"])
def health():
    logger.info("Health check called")
    return {"status": "ok"}


@app.post("/query", tags=["Query"])
def query_system(request: QueryRequest):
    cfg = load_config()
    show_qt = cfg.get("settings", {}).get("show_query_time", True)
    show_ts = cfg.get("settings", {}).get("show_token_speed", True)
    show_ct = cfg.get("settings", {}).get("show_chunk_timing", True)

    try:
        logger.info(f"Received query: system='{request.system}', question='{request.question}'")
        out = get_answer(request.system, request.question)

        # Unpack (answer, chunks, stats) with back-compat
        answer: Optional[str] = None
        sources = []
        stats = {}
        if isinstance(out, tuple):
            if len(out) >= 2:
                answer, sources = out[0], out[1]
            if len(out) >= 3:
                stats = out[2]
        else:
            answer = str(out)

        resp = {
            "system": request.system,
            "question": request.question,
            "answer": answer,
            "sources": sources,  # ALWAYS include raw chunk text for compatibility
        }

        if isinstance(stats, dict) and (show_qt or show_ts or show_ct):
            s = {}
            if show_qt and "query_time_sec" in stats:
                s["query_time_sec"] = stats["query_time_sec"]
            if show_ts and "tokens_per_sec" in stats:
                s.update({
                    "gen_time_sec": stats.get("gen_time_sec"),
                    "gen_tokens": stats.get("gen_tokens"),
                    "tokens_per_sec": stats.get("tokens_per_sec"),
                })
            if show_ct and "retrieval" in stats:
                s["retrieval"] = stats.get("retrieval", {})
                s["chunks_meta"] = stats.get("chunks_meta", [])
            if s:
                resp["stats"] = s

        return resp

    except Exception as e:
        logger.exception("Error processing query")
        return JSONResponse(status_code=500, content={"error": str(e)})


def _mount_web(app: FastAPI):
    env_dir = os.environ.get("RAG_WEB_DIR")
    if env_dir and os.path.isdir(env_dir):
        logger.info(f"Mounting webapp from env RAG_WEB_DIR: {env_dir}")
        app.mount("/", StaticFiles(directory=env_dir, html=True), name="web")
        return

    cwd_webapp = os.path.abspath(os.path.join(os.getcwd(), "webapp"))
    if os.path.isdir(cwd_webapp):
        logger.info(f"Mounting webapp from working dir: {cwd_webapp}")
        app.mount("/", StaticFiles(directory=cwd_webapp, html=True), name="web")
        return

    cwd_web = os.path.abspath(os.path.join(os.getcwd(), "web"))
    if os.path.isdir(cwd_web):
        logger.info(f"Mounting webapp from working dir: {cwd_web}")
        app.mount("/", StaticFiles(directory=cwd_web, html=True), name="web")
        return

    # packaged fallback (optional if shipped)
    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
    if os.path.isdir(pkg_dir):
        logger.info(f"Mounting packaged webapp: {pkg_dir}")
        app.mount("/", StaticFiles(directory=pkg_dir, html=True), name="web")
        return

    logger.warning("No web UI directory found (RAG_WEB_DIR /webapp /web or packaged). API still available at /query.")


_mount_web(app)


# --- Programmatic Uvicorn runner ---
def start_api_server():
    
    # reload=True only if you’re running from source; for pip installs, reload=False is safer
    uvicorn.run("rag_llm_api_pipeline.api.server:app", host="0.0.0.0", port=8000, reload=False)
