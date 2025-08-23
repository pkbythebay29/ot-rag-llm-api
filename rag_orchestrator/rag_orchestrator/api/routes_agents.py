from __future__ import annotations

from typing import List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Use the manager directly (avoid helper drift)
from ._state import manager
from ..agents.base import AgentSpec

router = APIRouter(prefix="/agents", tags=["agents"])


# ---------- Models ----------


class BulkCreateRequest(BaseModel):
    system: str = Field(..., description="System name (maps to a provider/system.yaml)")
    name_prefix: str = Field(..., description="Prefix for agent instance names")
    agents: List[str] = Field(..., description="Agent slugs, e.g. ['retriever']")
    copies: int = Field(
        1, ge=1, le=64, description="How many copies of each agent to start"
    )
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


# ---------- Helpers ----------


def _task_ready(task: Any) -> bool:
    # Try common flags
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
    # Single-CPU UX: default optimistic so the query box appears immediately.
    return True


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
    Uses manager.create(...) directly to avoid helper signature drift.
    """
    if not inp.agents:
        raise HTTPException(status_code=400, detail="No agents provided")

    started: List[StartedItem] = []

    for slug in inp.agents:
        for i in range(inp.copies):
            try:
                spec = AgentSpec(
                    name=f"{inp.name_prefix}-{slug}-{i}",
                    system=inp.system,
                    tenant=inp.tenant or "default",
                )
                task = await manager.create(slug, spec)
            except KeyError:
                raise HTTPException(
                    status_code=400, detail=f"Unknown agent slug: {slug}"
                )
            except HTTPException:
                raise
            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                raise HTTPException(
                    status_code=500, detail=f"Failed to start '{slug}': {e}\n{tb}"
                ) from e

            # Use the created name as a stable task_id and report ready now.
            task_id = spec.name
            started.append(
                StartedItem(
                    agent=slug,
                    task_id=task_id,
                    ready=True,  # optimistic ready for smooth UX
                    name=spec.name,
                    created_at=_task_created(task),
                )
            )

    if not started:
        raise HTTPException(
            status_code=500, detail="No agent started (manager.create returned nothing)"
        )

    return BulkCreateResponse(started=started)


@router.get("/status", response_model=AgentsStatusResponse)
async def agents_status():
    agents: List[AgentStatus] = []
    containers = []
    for attr in ("tasks", "handles", "registry", "instances"):
        if hasattr(manager, attr):
            try:
                containers.append(getattr(manager, attr))
            except Exception:
                pass

    seen = set()
    for c in containers:
        it = (
            c.items()
            if isinstance(c, dict)
            else enumerate(list(c))
            if hasattr(c, "__iter__")
            else []
        )
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
    candidates = []
    for attr in ("tasks", "handles", "registry", "instances"):
        if hasattr(manager, attr):
            try:
                candidates.append(getattr(manager, attr))
            except Exception:
                pass

    for c in candidates:
        if isinstance(c, dict):
            # direct key
            t = c.get(task_id)
            if t is not None:
                return {"task_id": task_id, "ready": _task_ready(t)}
            # match by 'name' too
            for v in c.values():
                if _task_name(v) == task_id:
                    return {"task_id": task_id, "ready": _task_ready(v)}
            # and by .id
            for v in c.values():
                if str(getattr(v, "id", _task_name(v))) == task_id:
                    return {"task_id": task_id, "ready": _task_ready(v)}
        else:
            try:
                for v in c:
                    if (
                        _task_name(v) == task_id
                        or str(getattr(v, "id", _task_name(v))) == task_id
                    ):
                        return {"task_id": task_id, "ready": _task_ready(v)}
            except Exception:
                pass

    return {"task_id": task_id, "ready": False}
