from __future__ import annotations

import os
import sys
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dependency
    psutil = None  # type: ignore[assignment]

try:
    import torch
except ImportError:  # pragma: no cover - optional runtime dependency
    torch = None  # type: ignore[assignment]

from rag_llm_api_pipeline.core import audit
from rag_llm_api_pipeline.core.feedback import record_quality_feedback
from rag_llm_api_pipeline.core.hitl import utc_now_iso
from rag_llm_api_pipeline.core.index_admin import get_index_status, list_index_statuses
from rag_llm_api_pipeline.core.index_worker import (
    get_index_worker_status,
    rebuild_index_in_worker,
)
from rag_llm_api_pipeline.core.platform_state import list_recent_routes
from rag_llm_api_pipeline.core.query_worker import get_query_worker_status
from rag_llm_api_pipeline.core.security import validate_api_key_header
from rag_llm_api_pipeline.core.system_assets import list_regulation_pools
from rag_llm_api_pipeline.core.system_metadata import get_system_metadata
from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.db import (
    compliance_store,
    metadata_store,
    regulation_pool_store,
    review_store,
)

router = APIRouter(tags=["Platform"])
SERVER_STARTED_AT = time.time()


def _cpu_percent() -> float:
    if psutil is None:
        return 0.0
    return float(psutil.cpu_percent(interval=None))


def _memory_snapshot() -> dict[str, float]:
    if psutil is None:
        return {
            "available_gb": 0.0,
            "total_gb": 0.0,
            "working_set_gb": 0.0,
        }

    memory = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    return {
        "available_gb": round(memory.available / (1024**3), 2),
        "total_gb": round(memory.total / (1024**3), 2),
        "working_set_gb": round(proc.memory_info().rss / (1024**3), 2),
    }


def _cuda_available() -> bool:
    return bool(torch is not None and torch.cuda.is_available())


def _ensure_orchestrator_import_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    orchestrator_root = os.path.join(repo_root, "rag_orchestrator")
    if os.path.isdir(orchestrator_root) and orchestrator_root not in sys.path:
        sys.path.insert(0, orchestrator_root)


def _get_orchestrator_status() -> dict[str, Any]:
    active_agents: list[dict[str, Any]] = []
    telemetry: dict[str, Any] = {}
    registered: list[str] = []
    try:
        _ensure_orchestrator_import_path()
        from rag_orchestrator.api._state import manager
        from rag_orchestrator.agents.registry import list_registered

        registered = list_registered()
        handles = getattr(manager, "handles", {}) or {}
        for handle in handles.values():
            active_agents.append(
                {
                    "task_id": getattr(handle, "id", ""),
                    "name": getattr(handle, "name", ""),
                    "agent_type": getattr(handle, "agent_type", ""),
                    "system": getattr(handle, "system", None),
                    "ready": bool(getattr(handle, "ready", True)),
                }
            )
        batchers = getattr(manager, "batchers", {}) or {}
        telemetry = {name: batcher.stats() for name, batcher in batchers.items()}
    except Exception:
        pass
    return {
        "active_agents": active_agents,
        "registered_agents": registered,
        "telemetry": telemetry,
    }


def _get_manager():
    _ensure_orchestrator_import_path()
    from rag_orchestrator.api._state import manager

    return manager


def _find_agent_handle(agent_ref: str) -> Any | None:
    handles = getattr(_get_manager(), "handles", {}) or {}
    if agent_ref in handles:
        return handles[agent_ref]
    for agent_id, handle in handles.items():
        if str(agent_id) == agent_ref:
            return handle
        if str(getattr(handle, "name", "")) == agent_ref:
            return handle
        if str(getattr(handle, "id", "")) == agent_ref:
            return handle
    return None


def _get_capacity_status(active_agents_count: int) -> dict[str, Any]:
    memory = _memory_snapshot()
    cpu_percent = _cpu_percent()
    available_gb = memory["available_gb"]
    total_gb = memory["total_gb"]
    reserved_buffer_gb = 2.0
    estimated_agent_gb = 1.5
    recommended_max_agents = max(
        1, int(max(0.0, available_gb - reserved_buffer_gb) // estimated_agent_gb)
    )
    has_memory_headroom = available_gb > (reserved_buffer_gb + estimated_agent_gb)
    cpu_constrained = cpu_percent >= 97.0 and active_agents_count > 0
    can_start = has_memory_headroom and not cpu_constrained
    reason = "Capacity available"
    if not has_memory_headroom:
        reason = "Not enough free memory for another agent"
    elif cpu_constrained:
        reason = "CPU is too busy for another agent"
    return {
        "can_start_another": can_start,
        "reason": reason,
        "active_agents": active_agents_count,
        "recommended_max_agents": recommended_max_agents,
        "available_memory_gb": available_gb,
        "total_memory_gb": total_gb,
        "cpu_percent": cpu_percent,
    }


def _read_log_tail(path: str, max_lines: int = 25) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    return [line.rstrip() for line in lines[-max_lines:]]


def _runtime_summary() -> dict[str, Any]:
    memory = _memory_snapshot()
    query_worker = get_query_worker_status()
    recent_logs = _read_log_tail(os.path.join(os.getcwd(), "uvicorn.err.log"))
    hint = "Server reachable."
    joined = "\n".join(recent_logs[-8:]).lower()
    if query_worker.get("state") == "running":
        hint = "Model worker is running. First query may take time while the local model warms up."
    elif query_worker.get("state") == "crashed":
        hint = "The isolated query worker crashed. This often points to model initialization or memory pressure."
    elif "loading checkpoint shards" in joined:
        hint = "Model warm-up is in progress. First query can take longer."
    elif "runtimeerror" in joined or "memory" in joined:
        hint = "Recent logs suggest a runtime or memory-related failure."
    return {
        "pid": os.getpid(),
        "uptime_sec": round(time.time() - SERVER_STARTED_AT, 1),
        "sampled_at": utc_now_iso(),
        "working_set_gb": memory["working_set_gb"],
        "available_memory_gb": memory["available_gb"],
        "cpu_percent": _cpu_percent(),
        "hint": hint,
        "query_worker": query_worker,
        "index_worker": get_index_worker_status(),
        "recent_logs": recent_logs,
    }


def _resolved_model_runtime(config: dict[str, Any]) -> dict[str, str]:
    models = config.get("models", {}) or {}
    settings = config.get("settings", {}) or {}
    configured_device = models.get("device") or "auto"
    use_cpu = bool(settings.get("use_cpu", False))
    if use_cpu:
        effective_device = "cpu"
    elif configured_device == "auto":
        effective_device = "cuda" if _cuda_available() else "cpu"
    elif configured_device == "cuda" and _cuda_available():
        effective_device = "cuda"
    else:
        effective_device = "cpu"

    configured_backend = str(models.get("quantization_backend", "auto"))
    backend_value = configured_backend.strip().lower()
    if backend_value in {"", "none", "off", "false", "disabled"}:
        effective_backend = "none"
    elif backend_value == "auto":
        effective_backend = "dynamic-int8" if effective_device == "cpu" else "none"
    elif effective_device == "cuda":
        effective_backend = "none"
    else:
        effective_backend = configured_backend

    return {
        "configured_device": configured_device,
        "effective_device": effective_device,
        "configured_quantization_backend": configured_backend,
        "effective_quantization_backend": effective_backend,
    }


def _get_refresh_seconds(config: dict[str, Any]) -> int:
    ui_cfg = config.get("ui", {}) or {}
    return max(1, int(ui_cfg.get("telemetry_refresh_seconds", 5)))


def _configuration_summary(config: dict[str, Any]) -> dict[str, Any]:
    runtime_model = _resolved_model_runtime(config)
    return {
        "system_metadata": get_system_metadata(),
        "refresh": {
            "telemetry_refresh_seconds": _get_refresh_seconds(config),
        },
        "models": {
            "llm_model": config.get("models", {}).get("llm_model"),
            "embedding_model": config.get("retriever", {}).get("embedding_model"),
            "device": runtime_model["configured_device"],
            "effective_device": runtime_model["effective_device"],
            "precision": config.get("models", {}).get("model_precision"),
            "quantization_backend": runtime_model["configured_quantization_backend"],
            "effective_quantization_backend": runtime_model[
                "effective_quantization_backend"
            ],
            "preset": config.get("llm", {}).get("preset"),
            "prompt_version": config.get("llm", {}).get("prompt_version"),
        },
        "paths": {
            "data_dir": os.path.abspath(
                config.get("settings", {}).get("data_dir", "data/manuals")
            ),
            "index_dir": os.path.abspath(
                config.get("retriever", {}).get("index_dir", "indices")
            ),
            "review_store": os.path.abspath(review_store.get_db_path()),
            "metadata_store": os.path.abspath(metadata_store.get_db_path()),
            "compliance_store": os.path.abspath(compliance_store.get_db_path()),
            "regulation_pool_store": os.path.abspath(regulation_pool_store.get_db_path()),
            "audit_log": os.path.abspath(
                config.get("audit", {}).get("log_path", "data/audit/audit_log.jsonl")
            ),
        },
        "hitl": config.get("hitl", {}),
        "compliance": config.get("compliance", {}),
    }


class QualityFeedbackRequest(BaseModel):
    trace_id: str = Field(..., description="Trace identifier for the rated response.")
    rating: str = Field(..., description="Response quality rating: good or bad.")
    system: str | None = None
    question: str | None = None
    response: str | None = None
    review_id: str | None = None


class AgentStartRequest(BaseModel):
    system: str = Field(..., description="System to bind the agent to.")
    agent_type: str = Field(
        default="retriever", description="Built-in agent slug to start."
    )
    name_prefix: str = Field(
        default="agent",
        description="Prefix used when creating the agent instance name.",
    )
    tenant: str | None = Field(default="default", description="Optional tenant label.")


class IndexRebuildResponse(BaseModel):
    system_name: str
    status: str
    report: dict[str, Any]
    worker: dict[str, Any]


@router.get(
    "/system/metadata",
    tags=["Configuration"],
    summary="Get system metadata",
    description="Return Krionis platform metadata including version, GAMP classification, and model/prompt placeholders.",
)
def get_metadata() -> dict[str, Any]:
    return get_system_metadata()


@router.get(
    "/platform/dashboard",
    summary="Get dashboard status",
    description="Return the current operator dashboard state, including models from YAML, active agents, review queue size, telemetry, and resource capacity.",
)
def get_dashboard_status() -> dict[str, Any]:
    config = load_config() or {}
    orchestrator = _get_orchestrator_status()
    index_statuses = list_index_statuses(config)
    configuration = _configuration_summary(config)
    return {
        "models": configuration["models"],
        "configuration": configuration,
        "refresh": configuration["refresh"],
        "pending_reviews": len(review_store.get_pending_reviews()),
        "compliance": compliance_store.get_summary(),
        "regulation_pools": list_regulation_pools(config),
        "indexes": index_statuses,
        "recent_routes": list_recent_routes(),
        "orchestrator": {
            **orchestrator,
            "capacity": _get_capacity_status(
                active_agents_count=len(orchestrator["active_agents"])
            ),
        },
        "runtime": _runtime_summary(),
    }


@router.get(
    "/platform/runtime",
    summary="Get runtime diagnostics",
    description="Return local runtime diagnostics including memory usage, uptime, and recent server log lines for UI troubleshooting.",
)
def get_runtime_status() -> dict[str, Any]:
    return _runtime_summary()


@router.get(
    "/platform/telemetry",
    tags=["telemetry"],
    summary="Get telemetry snapshot",
    description="Return agent inventory, microbatch telemetry, and recent routed query events for custom dashboards.",
)
def get_telemetry_status() -> dict[str, Any]:
    config = load_config() or {}
    orchestrator = _get_orchestrator_status()
    return {
        "sampled_at": utc_now_iso(),
        "refresh": {"telemetry_refresh_seconds": _get_refresh_seconds(config)},
        "orchestrator": {
            **orchestrator,
            "capacity": _get_capacity_status(
                active_agents_count=len(orchestrator["active_agents"])
            ),
        },
        "recent_routes": list_recent_routes(),
    }


@router.get(
    "/platform/configuration",
    tags=["Configuration"],
    summary="Get configuration snapshot",
    description="Return the active Krionis configuration, resolved model runtime, and local storage paths used by the platform.",
)
def get_configuration_snapshot() -> dict[str, Any]:
    config = load_config() or {}
    return _configuration_summary(config)


@router.get(
    "/platform/indexes",
    summary="Get retrieval index status",
    description="Return the configured source directory, source files, index file locations, and build status for each system.",
)
def get_index_statuses_route() -> dict[str, Any]:
    config = load_config() or {}
    return {
        "systems": list_index_statuses(config),
        "index_worker": get_index_worker_status(),
    }


@router.get(
    "/platform/indexes/{system_name}",
    summary="Get retrieval index status for one system",
    description="Return the source directory, index directory, and cache files used by the RAG retriever for a single system.",
)
def get_index_status_route(system_name: str) -> dict[str, Any]:
    try:
        return get_index_status(system_name, load_config() or {})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/platform/indexes/{system_name}/rebuild",
    summary="Rebuild retrieval index",
    description="Rebuild the retrieval cache for a system in an isolated worker process and return the build report.",
    response_model=IndexRebuildResponse,
)
def rebuild_index_route(system_name: str) -> IndexRebuildResponse:
    try:
        report = rebuild_index_in_worker(system_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return IndexRebuildResponse(
        system_name=system_name,
        status="rebuilt",
        report=report,
        worker=get_index_worker_status(),
    )


@router.get(
    "/platform/agents",
    summary="List active agents",
    description="Return all active orchestrator agents, including the stable task name used by the controlled query route.",
)
def get_active_agents_route() -> dict[str, Any]:
    orchestrator = _get_orchestrator_status()
    return {
        "items": orchestrator["active_agents"],
        "capacity": _get_capacity_status(
            active_agents_count=len(orchestrator["active_agents"])
        ),
    }


@router.post(
    "/platform/agents/start",
    summary="Start one agent",
    description="Start a built-in orchestrator agent and return its task identifier for subsequent controlled queries.",
)
async def start_agent_route(payload: AgentStartRequest) -> dict[str, Any]:
    try:
        from rag_orchestrator.agents.base import AgentSpec
        from rag_orchestrator.agents.registry import list_registered
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    registered = list_registered()
    if payload.agent_type not in registered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown agent slug: {payload.agent_type}",
        )

    handles = getattr(_get_manager(), "handles", {}) or {}
    suffix = len(handles) + 1
    spec = AgentSpec(
        name=f"{payload.name_prefix}{suffix}-{payload.agent_type}-0",
        system=payload.system,
        tenant=payload.tenant or "default",
    )
    handle = await _get_manager().create(payload.agent_type, spec)
    return {
        "task_id": handle.name,
        "handle_id": handle.id,
        "name": handle.name,
        "agent_type": handle.agent_type,
        "system": handle.system,
        "ready": handle.ready,
        "started_at": utc_now_iso(),
    }


@router.delete(
    "/platform/agents/{agent_ref}",
    summary="Stop one agent",
    description="Stop an active agent by task name or handle ID.",
)
async def stop_agent_route(agent_ref: str) -> dict[str, Any]:
    handle = _find_agent_handle(agent_ref)
    if handle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_ref}' was not found.",
        )
    await _get_manager().destroy(handle.id)
    return {
        "status": "stopped",
        "agent_ref": agent_ref,
        "handle_id": handle.id,
        "task_id": handle.name,
        "stopped_at": utc_now_iso(),
    }


@router.get(
    "/platform/routes/recent",
    summary="Get recent controlled query routes",
    description="Return the most recent controlled queries, including which agent handled each one and whether the result was approved or sent to review.",
)
def get_recent_routes(limit: int = 20) -> dict[str, Any]:
    return {"items": list_recent_routes(limit=limit)}


@router.get(
    "/platform/records",
    tags=["Records"],
    summary="Get stored result metadata",
    description="Return recent quality ratings and review decision records persisted in the local SQLite metadata store.",
)
def get_result_records(limit: int = 50) -> dict[str, Any]:
    return {
        "summary": metadata_store.get_summary(),
        "items": metadata_store.list_records(limit=limit),
        "database_path": os.path.abspath(metadata_store.get_db_path()),
        "compliance_summary": compliance_store.get_summary(),
    }


@router.post(
    "/feedback/quality",
    summary="Record response quality feedback",
    description="Record a Good or Bad operator rating for a response trace.",
)
def submit_quality_feedback(
    payload: QualityFeedbackRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    rating = payload.rating.strip().lower()
    if rating not in {"good", "bad"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rating must be 'good' or 'bad'.",
        )
    return record_quality_feedback(
        trace_id=payload.trace_id,
        rating=rating,
        system_id=payload.system,
        query=payload.question,
        response=payload.response,
        review_id=payload.review_id,
        user_id=x_user_id or "anonymous",
    )


@router.get(
    "/review/{review_id}",
    summary="Get a review item",
    description="Retrieve a specific HITL review item, including original response, reviewer notes, and final response if available.",
)
def get_review_item(
    review_id: str,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    item = review_store.get_review(review_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item '{review_id}' was not found.",
        )
    return item


@router.get(
    "/audit/traces/{trace_id}",
    summary="Get trace audit events",
    description="Return append-only audit events associated with a single query trace ID.",
)
def get_trace_audit_events(
    trace_id: str,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    events = audit.get_trace_events(trace_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit events found for trace '{trace_id}'.",
        )
    return {"trace_id": trace_id, "events": events}


@router.get(
    "/audit/reviews/{review_id}",
    summary="Get review audit events",
    description="Return append-only audit events associated with a review ID, including approval or rejection decisions.",
)
def get_review_audit_events(
    review_id: str,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    events = audit.get_review_events(review_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit events found for review '{review_id}'.",
        )
    return {"review_id": review_id, "events": events}
