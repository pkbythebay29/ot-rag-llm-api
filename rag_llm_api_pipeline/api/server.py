import logging
import os
from importlib.resources import as_file, files
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag_llm_api_pipeline import __version__
from rag_llm_api_pipeline.api.platform_routes import router as platform_router
from rag_llm_api_pipeline.api.review_routes import router as review_router
from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core import audit
from rag_llm_api_pipeline.core.hitl import (
    create_review_item,
    get_response_preview_chars,
    get_version_placeholders,
    requires_human_review,
    utc_now_iso,
)
from rag_llm_api_pipeline.core.orchestrator import get_orchestrator
from rag_llm_api_pipeline.core.security import get_user_id
from rag_llm_api_pipeline.db import review_store
from rag_llm_api_pipeline.ui.ui_routes import router as ui_router

"""
FastAPI server for RAG LLM API Pipeline
- Serves web UI (CWD -> env -> packaged)
- /health and /query endpoints
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Readiness and liveness endpoints for the Krionis API service.",
    },
    {
        "name": "Query",
        "description": "Primary query interface for submitting RAG requests through the Krionis HITL control layer.",
    },
    {
        "name": "Review",
        "description": "Human-in-the-loop review queue operations for approving or rejecting pending outputs.",
    },
    {
        "name": "Platform",
        "description": "System metadata and append-only audit retrieval endpoints for platform integrations.",
    },
    {
        "name": "UI",
        "description": "Internal browser-based interfaces used by operators and reviewers.",
    },
]


class QueryRequest(BaseModel):
    system: str = Field(
        ...,
        description="Logical system identifier configured in config/system.yaml.",
        examples=["TestSystem"],
    )
    question: str = Field(
        ...,
        description="Natural-language question to send through the Krionis query pipeline.",
        examples=["What is the restart sequence for this machine?"],
    )


def _build_trace(trace_id: str, status: str, stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "status": status,
        "steps": [
            {"stage": "query_received", "timestamp": utc_now_iso()},
            {"stage": "document_search_completed", "timestamp": utc_now_iso()},
            {"stage": "hitl_evaluated", "timestamp": utc_now_iso()},
        ],
        "stats": stats,
    }


def _format_stats(stats: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    show_qt = cfg.get("settings", {}).get("show_query_time", True)
    show_ts = cfg.get("settings", {}).get("show_token_speed", True)
    show_ct = cfg.get("settings", {}).get("show_chunk_timing", True)

    if not isinstance(stats, dict) or not (show_qt or show_ts or show_ct):
        return {}

    formatted: dict[str, Any] = {}
    if show_qt and "query_time_sec" in stats:
        formatted["query_time_sec"] = stats["query_time_sec"]
    if show_ts and "tokens_per_sec" in stats:
        formatted.update(
            {
                "gen_time_sec": stats.get("gen_time_sec"),
                "gen_tokens": stats.get("gen_tokens"),
                "tokens_per_sec": stats.get("tokens_per_sec"),
            }
        )
    if show_ct and "retrieval" in stats:
        formatted["retrieval"] = stats.get("retrieval", {})
        formatted["chunks_meta"] = stats.get("chunks_meta", [])
    return formatted


def create_app() -> FastAPI:
    app = FastAPI(
        title="Krionis Pipeline API",
        summary="Human-in-the-loop controlled RAG API for compliant industrial knowledge workflows.",
        description=(
            "Krionis exposes a traceable RAG API with mandatory HITL controls for flagged responses, "
            "append-only audit logging, and future-ready orchestrator hooks. "
            "Use the interactive docs for request/response schemas and the review/audit APIs to build external tooling."
        ),
        version=__version__,
        contact={
            "name": "Krionis Platform",
            "url": "https://krionis.com",
        },
        openapi_tags=OPENAPI_TAGS,
        docs_url="/api/docs",
        redoc_url="/api/reference",
        openapi_url="/api/openapi.json",
    )
    app.include_router(review_router)
    app.include_router(platform_router)
    app.include_router(ui_router)

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        logger.info("Health check called")
        review_store.init_db()
        return {"status": "ok"}

    @app.post("/query", tags=["Query"], response_model=None)
    def query_system(
        payload: QueryRequest,
        _: Request,
        x_user_id: str | None = Header(default=None),
    ) -> dict[str, Any] | JSONResponse:
        cfg = load_config()
        trace_id = str(uuid4())
        user_id = get_user_id(x_user_id, default="anonymous")
        model_version, prompt_version = get_version_placeholders()

        try:
            logger.info(
                "Received query: system='%s', question='%s'",
                payload.system,
                payload.question,
            )
            result = get_orchestrator().run_query(
                system_name=payload.system,
                question=payload.question,
            )
            answer = str(result.get("answer") or "")
            sources = list(result.get("sources") or [])
            stats = dict(result.get("stats") or {})
            retrieved_documents = list(result.get("retrieved_documents") or [])
            formatted_stats = _format_stats(stats, cfg)
            trace = _build_trace(trace_id, "evaluated", formatted_stats)

            if requires_human_review(payload.question, answer):
                review_item = create_review_item(
                    payload.question,
                    answer,
                    system_id=payload.system,
                    user_id=user_id,
                    trace_id=trace_id,
                    retrieved_documents=retrieved_documents,
                    response_preview=answer[: get_response_preview_chars()],
                )
                review_store.save_review(review_item)
                trace["steps"].append(
                    {"stage": "review_queued", "timestamp": utc_now_iso()}
                )
                audit.log_query_event(
                    trace_id=trace_id,
                    system_id=payload.system,
                    query=payload.question,
                    generated_response=answer,
                    final_response=None,
                    retrieved_documents=retrieved_documents,
                    user_id=user_id,
                    model_version=model_version,
                    prompt_version=prompt_version,
                    status="pending_review",
                    reviewer_decision="pending_review",
                    review_id=review_item["id"],
                    execution_trace=trace,
                    sources=sources,
                )
                response: dict[str, Any] = {
                    "status": "pending_review",
                    "trace_id": trace_id,
                    "review_id": review_item["id"],
                    "system": payload.system,
                    "question": payload.question,
                    "response_preview": review_item["response_preview"],
                }
                if formatted_stats:
                    response["stats"] = formatted_stats
                return response

            trace["steps"].append({"stage": "auto_approved", "timestamp": utc_now_iso()})
            audit.log_query_event(
                trace_id=trace_id,
                system_id=payload.system,
                query=payload.question,
                generated_response=answer,
                final_response=answer,
                retrieved_documents=retrieved_documents,
                user_id=user_id,
                model_version=model_version,
                prompt_version=prompt_version,
                status="approved",
                reviewer_decision="auto_approved",
                review_id=None,
                execution_trace=trace,
                sources=sources,
            )

            response = {
                "status": "approved",
                "trace_id": trace_id,
                "system": payload.system,
                "question": payload.question,
                "answer": answer,
                "sources": sources,
            }
            if formatted_stats:
                response["stats"] = formatted_stats
            return response

        except Exception as exc:
            logger.exception("Error processing query")
            return JSONResponse(status_code=500, content={"error": str(exc)})

    _mount_web(app)
    return app


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
        logger.warning(
            "RAG_WEB_DIR set to '%s' but index.html not found. Ignoring.", env_dir
        )

    # 3) Packaged
    try:
        pkg_web = files("rag_llm_api_pipeline").joinpath("web")
        with as_file(pkg_web) as pkg_path:
            index_path = pkg_path / "index.html"
            if pkg_path.is_dir() and index_path.is_file():
                logger.info("Mounting packaged webapp: %s", pkg_path)
                app_.mount(
                    "/", StaticFiles(directory=str(pkg_path), html=True), name="web"
                )
                return
            logger.warning(
                "Packaged web exists but index.html not found at: %s", index_path
            )
    except Exception:
        logger.exception(
            "Failed to access packaged web directory via importlib.resources."
        )

    logger.warning(
        "No web UI directory found with index.html. API available at /query."
    )


app = create_app()


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
