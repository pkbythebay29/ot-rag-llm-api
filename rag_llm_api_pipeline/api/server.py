import os
import logging
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from importlib.resources import files, as_file

from rag_llm_api_pipeline.retriever import get_answer
from rag_llm_api_pipeline.config_loader import load_config

import uvicorn

"""
FastAPI server for RAG LLM API Pipeline
- Serves web UI (CWD -> env -> packaged)
- /health and /query endpoints
"""

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


@app.post("/query", tags=["Query"], response_model=None)
def query_system(request: QueryRequest) -> dict[str, Any] | JSONResponse:
    cfg = load_config()
    show_qt = cfg.get("settings", {}).get("show_query_time", True)
    show_ts = cfg.get("settings", {}).get("show_token_speed", True)
    show_ct = cfg.get("settings", {}).get("show_chunk_timing", True)

    try:
        logger.info("Received query: system='%s', question='%s'", request.system, request.question)
        out = get_answer(request.system, request.question)

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

        resp: dict[str, Any] = {
            "system": request.system,
            "question": request.question,
            "answer": answer,
            "sources": sources,
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


def _dir_has_index_html(path: str) -> bool:
    return os.path.isdir(path) and os.path.isfile(os.path.join(path, "index.html"))


def _mount_web(app_: FastAPI) -> None:
    """
    Mount static UI with priority:
      1) CWD: ./webapp or ./web (must contain index.html)
      2) Env: RAG_WEB_DIR (must contain index.html)
      3) Packaged: rag_llm_api_pipeline/web
    """
    # 1) CWD
    cwd = os.getcwd()
    for rel in ("webapp", "web"):
        candidate = os.path.abspath(os.path.join(cwd, rel))
        if _dir_has_index_html(candidate):
            logger.info("Mounting webapp from working dir: %s", candidate)
            app_.mount("/", StaticFiles(directory=candidate, html=True), name="web")
            return
        elif os.path.isdir(candidate):
            logger.warning("Found '%s' but no index.html. Skipping.", candidate)

    # 2) Env
    env_dir = os.environ.get("RAG_WEB_DIR")
    if env_dir and _dir_has_index_html(env_dir):
        logger.info("Mounting webapp from env RAG_WEB_DIR: %s", env_dir)
        app_.mount("/", StaticFiles(directory=env_dir, html=True), name="web")
        return
    elif env_dir:
        logger.warning("RAG_WEB_DIR set to '%s' but index.html not found. Ignoring.", env_dir)

    # 3) Packaged
    try:
        pkg_web = files("rag_llm_api_pipeline").joinpath("web")
        with as_file(pkg_web) as pkg_path:
            index_path = pkg_path / "index.html"
            if pkg_path.is_dir() and index_path.is_file():
                logger.info("Mounting packaged webapp: %s", pkg_path)
                app_.mount("/", StaticFiles(directory=str(pkg_path), html=True), name="web")
                return
            logger.warning("Packaged web exists but index.html not found at: %s", index_path)
    except Exception:
        logger.exception("Failed to access packaged web directory via importlib.resources.")

    logger.warning("No web UI directory found with index.html. API available at /query.")


_mount_web(app)


def start_api_server() -> None:
    """Programmatic Uvicorn runner."""
    uvicorn.run(
        "rag_llm_api_pipeline.api.server:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    start_api_server()
