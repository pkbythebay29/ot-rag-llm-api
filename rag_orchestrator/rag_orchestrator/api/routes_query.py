# rag_orchestrator/api/routes_query.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ._state import manager
from .config_bridge import resolve_system_yaml
from ..providers.rag_llm_api_provider import RagLLMApiProvider

router = APIRouter(prefix="", tags=["query"])

# ---- paths for system.yaml (your repo has config/system.yaml) ----
# routes_query.py -> rag_orchestrator/api -> parents[2] points to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEMS_ROOT = REPO_ROOT / "config"          # e.g. E:/rag_llm_api_pipeline/config
FALLBACK_YAML = "system.yaml"                # inside SYSTEMS_ROOT

# ---- lightweight local provider pool ----
class _LocalProviderPool:
    def __init__(self) -> None:
        self._cache: dict[str, RagLLMApiProvider] = {}

    def get(self, system_name: str) -> RagLLMApiProvider:
        if system_name in self._cache:
            return self._cache[system_name]
        path = resolve_system_yaml(
            system_name,
            systems_root=SYSTEMS_ROOT,
            fallback_yaml=FALLBACK_YAML,
        )
        prov = RagLLMApiProvider(path)
        self._cache[system_name] = prov
        return prov

_provider_pool = _LocalProviderPool()

# ---- models ----
class QueryRequest(BaseModel):
    task_id: str = Field(..., description="Agent/task id (e.g., session1-retriever-0)")
    question: str
    context: Optional[str] = None
    system: Optional[str] = None  # optional override

class QueryResponse(BaseModel):
    text: str
    stats: dict = {}
    cache_hit: bool = False

# ---- helpers ----
def _find_task(task_id: str) -> Any | None:
    """Locate a task/agent handle by id or name across common containers."""
    candidates = []
    for attr in ("tasks", "handles", "registry", "instances"):
        if hasattr(manager, attr):
            try:
                candidates.append(getattr(manager, attr))
            except Exception:
                pass

    for c in candidates:
        if isinstance(c, dict):
            t = c.get(task_id)
            if t is not None:
                return t
            for v in c.values():
                vid = str(getattr(v, "id", None) or getattr(v, "name", None))
                if vid == task_id:
                    return v
        else:
            try:
                for v in c:
                    vid = str(getattr(v, "id", None) or getattr(v, "name", None))
                    if vid == task_id:
                        return v
            except Exception:
                pass
    return None

def _extract_system_from_task(task: Any) -> Optional[str]:
    for attr in ("system",):
        if hasattr(task, attr):
            try:
                v = getattr(task, attr)
                return str(v() if callable(v) else v)
            except Exception:
                pass
    spec = getattr(task, "spec", None)
    if spec is not None and hasattr(spec, "system"):
        try:
            return str(spec.system)
        except Exception:
            pass
    return None

# ---- route ----
@router.post("/query", response_model=QueryResponse)
async def orchestrator_query(inp: QueryRequest):
    """
    Submit a question to an agent (agent-first). If the agent can't accept work,
    fall back to the provider (direct pipeline via system.yaml).
    """
    task = _find_task(inp.task_id)

    # A) Try the agent path first (exercises micro-batching if the task supports it)
    agent_err: Optional[Exception] = None
    if task is not None:
        payload = {"question": inp.question, "context": inp.context or ""}
        for method_name in ("submit", "handle"):
            if hasattr(task, method_name):
                try:
                    fn = getattr(task, method_name)
                    out = fn(payload)
                    if hasattr(out, "__await__"):
                        out = await out
                    # normalize common shapes
                    if isinstance(out, tuple) and len(out) == 2:
                        text, stats = out
                        return QueryResponse(
                            text=str(text or ""),
                            stats=dict(stats or {}),
                            cache_hit=bool((stats or {}).get("cache_hit", False)),
                        )
                    if isinstance(out, dict) and "text" in out:
                        return QueryResponse(
                            text=str(out.get("text") or ""),
                            stats=dict(out.get("stats", {}) or {}),
                            cache_hit=bool(out.get("cache_hit", False)),
                        )
                    return QueryResponse(text=str(out or ""), stats={})
                except Exception as e:
                    agent_err = e
                    break  # fall back to provider

    # B) Provider fallback (direct pipeline via system.yaml)
    system = (
        inp.system
        or (_extract_system_from_task(task) if task is not None else None)
        or "TestSystem"
    )
    try:
        prov = _provider_pool.get(system)
        text, stats = prov.query(inp.question, inp.context or "")
        return QueryResponse(
            text=str(text or ""),
            stats=dict(stats or {}),
            cache_hit=bool((stats or {}).get("cache_hit", False)),
        )
    except Exception as e:
        detail = f"Agent path failed: {agent_err}" if agent_err else "Agent path unavailable"
        raise HTTPException(status_code=500, detail=f"{detail}; provider fallback failed: {e}")
