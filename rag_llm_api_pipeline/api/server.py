import os
import logging
from typing import Any, Optional, Union
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_llm_api_pipeline.retriever import get_answer
from rag_llm_api_pipeline.config_loader import load_config

import uvicorn

"""
FastAPI server for RAG LLM API Pipeline
- Serves web UI (from CWD/webapp or fallbacks)
- /health and /query endpoints
- Optional stats in response (controlled via YAML)
"""

# --- Type alias for JSON-friendly data ---
JSONValue = Union[
    str,
    int,
    float,
    bool,
    None,
    dict[str, "JSONValue"],
    list["JSONValue"],
]

app = FastAPI(title="RAG LLM API Pipeline")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    system: str
    question: str


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    logger.info("Health check called")
    return {"status": "ok"}


@app.post("/query", tags=["Query"])
def query_system(request: QueryRequest) -> dict[str, JSONValue] | JSONResponse:
    cfg = load_config()
    show_qt = cfg.get("settings", {}).get("show_query_time", True)
    show_ts = cfg.get("settings", {}).get("show_token_speed", True)
    show_ct = cfg.get("settings", {}).get("show_chunk_timing", True)

    try:
        logger.info(
            "Received query: system='%s', question='%s'",
            request.system,
            request.question,
        )
        out = get_answer(request.system, request.question)

        # Unpack (answer, chunks, stats) with back-compat
        answer: Optional[str] = None
        sources: list[Any] = []
        stats: dict[str, Any] = {}
        if isinstance(out, tuple):
            if len(out) >= 2:
                answer, sources = out[0], out[1]
            if len(out) >= 3:
                stats = out[2]
        else:
            answer = str(out)

        resp: dict[str, JSONValue] = {
            "system": request.system,
            "question": request.question,
            "answer": answer,
            "sources": sources,  # ALWAYS include raw chunk text for compatibility
        }

        if isinstance(stats, dict) and (show_qt or show_ts or show_ct):
            s: dict[str, Any] = {}
            if show_qt and "query_time_sec" in stats:
                s["query_time_sec"] = stats["query_time_sec"]
            if show_ts and "tokens_per_sec" in stats:
                s.update(
                    {
                        "gen_time_sec": stats.get("gen_time_sec"),
                        "gen_tokens": stats.get("gen_tokens"),
                        "tokens_per_sec": stats.get("tokens_per_sec"),
                    }
                )
            if show_ct and "retrieval" in stats:
                s["retrieval"] = stats.get("retrieval", {})
                s["chunks_meta"] = stats.get("chunks_meta", [])
            if s:
                resp["stats"] = s

        return resp

    except Exception as e:
        logger.exception("Error processing query")
        return JSONResponse(status_code=500, content={"error": str(e)})


def _mount_web(app_: FastAPI) -> None:
    env_dir = os.environ.get("RAG_WEB_DIR")
    if env_dir and os.path.isdir(env_dir):
        logger.info("Mounting webapp from env RAG_WEB_DIR: %s", env_dir)
        app_.mount("/", StaticFiles(directory=env_dir, html=True), name="web")
        return

    cwd_webapp = os.path.abspath(os.path.join(os.getcwd(), "webapp"))
    if os.path.isdir(cwd_webapp):
        logger.info("Mounting webapp from working dir: %s", cwd_webapp)
        app_.mount("/", StaticFiles(directory=cwd_webapp, html=True), name="web")
        return

    cwd_web = os.path.abspath(os.path.join(os.getcwd(), "web"))
    if os.path.isdir(cwd_web):
        logger.info("Mounting webapp from working dir: %s", cwd_web)
        app_.mount("/", StaticFiles(directory=cwd_web, html=True), name="web")
        return

    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
    if os.path.isdir(pkg_dir):
        logger.info("Mounting packaged webapp: %s", pkg_dir)
        app_.mount("/", StaticFiles(directory=pkg_dir, html=True), name="web")
        return

    logger.warning(
        "No web UI directory found (RAG_WEB_DIR /webapp /web or packaged). "
        "API still available at /query."
    )


_mount_web(app)


# --- Programmatic Uvicorn runner ---
def start_api_server() -> None:
    # reload=True only if running from source; for pip installs, reload=False is safer
    uvicorn.run(
        "rag_llm_api_pipeline.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
