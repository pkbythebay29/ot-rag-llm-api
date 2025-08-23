from __future__ import annotations
from fastapi import APIRouter
from ._state import manager

router = APIRouter(prefix="", tags=["telemetry"])

@router.get("/telemetry")
async def telemetry():
    """
    Return stats for all known batchers.
    """
    batchers = getattr(manager, "batchers", {}) or {}
    return {k: v.stats() for k, v in batchers.items()}

@router.get("/queue/{task_id}")
async def queue_snapshot(task_id: str):
    """
    Return snapshot of the pending queue for a specific batcher.
    Includes position, ticket id, age in seconds, and optional meta (e.g. tenant).
    """
    batchers = getattr(manager, "batchers", {}) or {}
    b = batchers.get(task_id)
    if not b:
        return {"task_id": task_id, "pending": 0, "items": []}
    items = b.pending_snapshot()
    return {
        "task_id": task_id,
        "pending": b.stats()["pending"],
        "items": items,
    }
