from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Reuse your manager + helper from api/_state.py
from ._state import manager, ensure_started_task


router = APIRouter(prefix="/agents", tags=["agents"])


# ---------- Models ----------

class BulkCreateRequest(BaseModel):
    system: str = Field(..., description="System name (maps to a provider/system.yaml)")
    name_prefix: str = Field(..., description="Prefix for agent instance names")
    agents: List[str] = Field(..., description="Agent slugs, e.g. ['retriever']")
    copies: int = Field(1, ge=1, le=64, description="How many copies of each agent to start")
    tenant: Optional[str] = Field("default", description="Multi-tenant label")


class StartedItem(BaseModel):
    agent: str
    task_id: str
    ready: bool = False
    name: Optional[str] = None
    created_at: float


class BulkCreateResponse(BaseModel):
    started: List[StartedItem]


class AgentStatus(BaseModel):
    agent: str
    task_id: str
    ready: bool
    name: Optional[str]
    created_at: float


class AgentsStatusResponse(BaseModel):
    agents: List[AgentStatus]


# ---------- Helpers (defensive; work with your current Manager/Task API) ----------

def _task_ready(task: Any) -> bool:
    """
    Best-effort readiness check that doesn't assume a specific Task API.
    Falls back to False if we can't tell.
    """
    # Common patterns: .ready, .is_ready(), .started, .started_event.is_set()
    for attr in ("ready", "is_ready", "started"):
        if hasattr(task, attr):
            val = getattr(task, attr)
            try:
                return bool(val() if callable(val) else val)
            except Exception:
                pass
    # Event-like attribute
    ev = getattr(task, "started_event", None)
    if ev is not None:
        try:
            return bool(ev.is_set())
        except Exception:
            pass
    return False


def _task_name(task: Any) -> Optional[str]:
    for attr in ("name", "agent_name", "id"):
        if hasattr(task, attr):
            try:
                val = getattr(task, attr)
                return str(val() if callable(val) else val)
            except Exception:
                pass
    return None


def _task_created(task: Any) -> float:
    # Seconds since epoch; if unknown, use "now"
    for attr in ("created_at", "created", "ts", "timestamp"):
        if hasattr(task, attr):
            try:
                val = getattr(task, attr)
                v = val() if callable(val) else val
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, datetime):
                    return v.timestamp()
            except Exception:
                pass
    return datetime.utcnow().timestamp()


# ---------- Routes ----------

@router.post("/bulk", response_model=BulkCreateResponse)
async def bulk_create(inp: BulkCreateRequest):
    """
    Start N copies for each requested agent slug and return task handles.
    """
    if not inp.agents:
        raise HTTPException(status_code=400, detail="No agents provided")

    started: List[StartedItem] = []
    for t in inp.agents:
        for i in range(inp.copies):
            # ensure_started_task is already in your repo and returns a task/handle
            try:
                task = await ensure_started_task(
                    manager=manager,
                    system_name=inp.system,
                    agent_slug=t,
                    name_prefix=inp.name_prefix,
                    tenant=inp.tenant or "default",
                )
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Unknown agent slug: {t}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to start '{t}': {e}")

            # Gather minimal status so the UI can decide when to render query boxes
            started.append(
                StartedItem(
                    agent=t,
                    task_id=str(getattr(task, "id", _task_name(task) or f"{t}-{i}")),
                    ready=_task_ready(task),
                    name=_task_name(task),
                    created_at=_task_created(task),
                )
            )
    return BulkCreateResponse(started=started)


@router.get("/status", response_model=AgentsStatusResponse)
async def agents_status():
    """
    Return readiness for all known tasks.
    We introspect the manager without assuming its internal shape too much.
    """
    agents: List[AgentStatus] = []
    # Try common containers: manager.tasks, manager.handles, manager.registry
    containers = []
    for attr in ("tasks", "handles", "registry", "instances"):
        if hasattr(manager, attr):
            try:
                containers.append(getattr(manager, attr))
            except Exception:
                pass

    seen = set()
    for c in containers:
        # dict-like
        if isinstance(c, dict):
            it = c.items()
        else:
            # list/iterable of tasks
            try:
                it = enumerate(list(c))
            except Exception:
                continue

        for key, task in it:
            task_id = str(getattr(task, "id", _task_name(task) or key))
            if task_id in seen:
                continue
            seen.add(task_id)
            agents.append(
                AgentStatus(
                    agent=str(getattr(task, "agent", getattr(task, "kind", "unknown"))),
                    task_id=task_id,
                    ready=_task_ready(task),
                    name=_task_name(task),
                    created_at=_task_created(task),
                )
            )

    return AgentsStatusResponse(agents=agents)


@router.get("/ready")
async def agent_ready(task_id: str = Query(..., description="Task/agent id to check")):
    """
    Lightweight check: is a specific agent ready?
    The UI can poll this to decide when to render the query box.
    """
    # Probe through likely containers
    candidates = []
    for attr in ("tasks", "handles", "registry", "instances"):
        if hasattr(manager, attr):
            try:
                candidates.append(getattr(manager, attr))
            except Exception:
                pass

    for c in candidates:
        # dict
        if isinstance(c, dict):
            t = c.get(task_id)
            if t is not None:
                return {"task_id": task_id, "ready": _task_ready(t)}
            # also try values where .id matches
            for v in c.values():
                if str(getattr(v, "id", _task_name(v))) == task_id:
                    return {"task_id": task_id, "ready": _task_ready(v)}
        else:
            # iterable
            try:
                for v in c:
                    if str(getattr(v, "id", _task_name(v))) == task_id:
                        return {"task_id": task_id, "ready": _task_ready(v)}
            except Exception:
                pass

    # Not found — return false instead of 404 so UI can keep polling
    return {"task_id": task_id, "ready": False}
