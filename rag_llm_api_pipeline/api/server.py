import logging
import os
import sys
from importlib.resources import as_file, files
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag_llm_api_pipeline import __version__
from rag_llm_api_pipeline.api.compliance_routes import router as compliance_router
from rag_llm_api_pipeline.api.platform_routes import router as platform_router
from rag_llm_api_pipeline.api.review_routes import router as review_router
from rag_llm_api_pipeline.core.controlled import (
    build_controlled_response,
    execute_query_with_runtime,
)
from rag_llm_api_pipeline.core.security import get_user_id
from rag_llm_api_pipeline.db import compliance_store, metadata_store, review_store
from rag_llm_api_pipeline.ui.ui_routes import root_router, router as ui_router

"""
FastAPI server for Krionis Platform
- Serves web UI (CWD -> env -> packaged)
- /health and /query endpoints
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _ensure_orchestrator_import_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    orchestrator_root = os.path.join(repo_root, "rag_orchestrator")
    if os.path.isdir(orchestrator_root) and orchestrator_root not in sys.path:
        sys.path.insert(0, orchestrator_root)


def _wire_orchestrator(app: FastAPI) -> None:
    try:
        _ensure_orchestrator_import_path()
        from rag_orchestrator.api.imports import load_builtin_agents
        from rag_orchestrator.api.routes_agents import (
            router as orchestrator_agents_router,
        )
        from rag_orchestrator.api.routes_catalog import (
            router as orchestrator_catalog_router,
        )
        from rag_orchestrator.api.routes_telemetry import (
            router as orchestrator_telemetry_router,
        )
        from rag_orchestrator.agents.registry import list_registered
        from rag_orchestrator.api._state import schedule_startup

        load_builtin_agents()
        app.include_router(orchestrator_agents_router, prefix="/orchestrator")
        app.include_router(orchestrator_catalog_router, prefix="/orchestrator")
        app.include_router(orchestrator_telemetry_router, prefix="/orchestrator")

        @app.get("/orchestrator/diag/agents", tags=["diagnostics"])
        def orchestrator_diag_agents() -> dict[str, list[str]]:
            return {"registered": list_registered()}

        @app.on_event("startup")
        async def _start_orchestrator_runtime() -> None:
            schedule_startup()

    except Exception:
        logger.exception("Failed to wire orchestrator routes into the main API.")


def _get_agent_runtime_selection(agent_ref: str) -> dict[str, Any]:
    try:
        _ensure_orchestrator_import_path()
        from rag_orchestrator.api._state import manager

        handles = getattr(manager, "handles", {}) or {}
        handle = handles.get(agent_ref)
        if handle is None:
            for value in handles.values():
                if str(getattr(value, "name", "")) == agent_ref:
                    handle = value
                    break
                if str(getattr(value, "id", "")) == agent_ref:
                    handle = value
                    break
        if handle is None:
            return {}
        spec = getattr(handle, "spec", None)
        config = getattr(spec, "config", None) if spec is not None else None
        return dict(config or {})
    except Exception:
        return {}


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
        "name": "Compliance",
        "description": "Regulated-document assessment APIs that compare submitted documents against indexed regulation corpora.",
    },
    {
        "name": "Platform",
        "description": "System metadata and append-only audit retrieval endpoints for platform integrations.",
    },
    {
        "name": "Configuration",
        "description": "Resolved YAML configuration, local paths, and runtime settings surfaced for external consoles.",
    },
    {
        "name": "Records",
        "description": "Stored quality ratings and review-decision metadata for local analytics and QA workflows.",
    },
    {
        "name": "agents",
        "description": "Agent lifecycle endpoints for starting and inspecting orchestrator workers.",
    },
    {
        "name": "telemetry",
        "description": "Live orchestrator and microbatch telemetry endpoints.",
    },
    {
        "name": "catalog",
        "description": "Available built-in orchestrator agent types.",
    },
    {
        "name": "diagnostics",
        "description": "Diagnostics for built-in agent registration and provider connectivity.",
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
    runtime_profile: str | None = Field(
        default=None,
        description="Optional named runtime profile for inference and embeddings.",
    )
    inference_model: str | None = Field(
        default=None,
        description="Optional Hugging Face inference model key or identifier.",
    )
    embedding_model: str | None = Field(
        default=None,
        description="Optional Hugging Face embedding model key or identifier.",
    )


class ControlledAgentQueryRequest(BaseModel):
    task_id: str = Field(
        ...,
        description="Started agent task identifier or agent name.",
        examples=["session1-retriever-0"],
    )
    system: str = Field(
        ...,
        description="Logical system identifier configured in config/system.yaml.",
        examples=["TestSystem"],
    )
    question: str = Field(
        ...,
        description="Natural-language question to route through the orchestrator.",
        examples=["What is the restart sequence for this machine?"],
    )
    context: str | None = Field(
        default="",
        description="Optional additional context provided with the query.",
    )
    runtime_profile: str | None = Field(
        default=None,
        description="Optional runtime profile override for this query.",
    )
    inference_model: str | None = Field(
        default=None,
        description="Optional inference model override for this query.",
    )
    embedding_model: str | None = Field(
        default=None,
        description="Optional embedding model override for this query.",
    )


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
    app.include_router(compliance_router)
    app.include_router(review_router)
    app.include_router(platform_router)
    app.include_router(ui_router)
    app.include_router(root_router)
    _wire_orchestrator(app)

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        logger.info("Health check called")
        review_store.init_db()
        metadata_store.init_db()
        compliance_store.init_db()
        return {"status": "ok"}

    @app.post("/query", tags=["Query"], response_model=None)
    def query_system(
        payload: QueryRequest,
        _: Request,
        x_user_id: str | None = Header(default=None),
    ) -> dict[str, Any] | JSONResponse:
        trace_id = str(uuid4())
        user_id = get_user_id(x_user_id, default="anonymous")

        try:
            logger.info(
                "Received query: system='%s', question='%s'",
                payload.system,
                payload.question,
            )
            runtime_selection = payload.model_dump(
                include={"runtime_profile", "inference_model", "embedding_model"},
                exclude_none=True,
            )
            result = execute_query_with_runtime(
                payload.system,
                payload.question,
                runtime_selection=runtime_selection,
            )
            return build_controlled_response(
                system_id=payload.system,
                question=payload.question,
                result=result,
                user_id=user_id,
                trace_id=trace_id,
                route_name="direct_query",
                runtime_selection=runtime_selection,
            )

        except Exception as exc:
            logger.exception("Error processing query")
            return JSONResponse(status_code=500, content={"error": str(exc)})

    @app.post("/orchestrator/query", tags=["Query"], response_model=None)
    async def query_orchestrated_system(
        payload: ControlledAgentQueryRequest,
        _: Request,
        x_user_id: str | None = Header(default=None),
    ) -> dict[str, Any] | JSONResponse:
        trace_id = str(uuid4())
        user_id = get_user_id(x_user_id, default="anonymous")

        try:
            logger.info(
                "Received orchestrated query: task_id='%s', system='%s', question='%s'",
                payload.task_id,
                payload.system,
                payload.question,
            )
            # Agent lifecycle remains in the orchestrator, but all answer generation
            # is isolated in the dedicated query worker so the web server stays alive
            # during cold model load or heavy local inference.
            runtime_selection = {
                **_get_agent_runtime_selection(payload.task_id),
                **payload.model_dump(
                    include={"runtime_profile", "inference_model", "embedding_model"},
                    exclude_none=True,
                ),
            }
            result = execute_query_with_runtime(
                payload.system,
                payload.question,
                runtime_selection=runtime_selection,
            )
            return build_controlled_response(
                system_id=payload.system,
                question=payload.question,
                result=result,
                user_id=user_id,
                trace_id=trace_id,
                route_name="orchestrator_query",
                agent_task_id=payload.task_id,
                runtime_selection=runtime_selection,
            )

        except Exception as exc:
            logger.exception("Error processing orchestrated query")
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
