# rag_orchestrator/api/routes_query.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ._state import manager
from .config_bridge import resolve_system_yaml
from ..providers.rag_llm_api_provider import RagLLMApiProvider

# ### NEW
from ..batching.microbatch import AsyncMicroBatcher
import asyncio

router = APIRouter(prefix="", tags=["query"])

# ---- paths for system.yaml (your repo has config/system.yaml) ----
REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEMS_ROOT = REPO_ROOT / "config"  # e.g. E:/rag_llm_api_pipeline/config
FALLBACK_YAML = "system.yaml"  # inside SYSTEMS_ROOT


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


# ---- NEW: fallback batcher pool ----
class _FallbackBatcherPool:  # ### NEW
    def __init__(self) -> None:  # ### NEW
        self._cache: dict[str, AsyncMicroBatcher] = {}  # ### NEW

    def get(self, system_name: str) -> AsyncMicroBatcher:  # ### NEW
        if system_name in self._cache:  # ### NEW
            return self._cache[system_name]  # ### NEW

        prov = _provider_pool.get(system_name)  # ### NEW

        async def forward_fn(batch: list[dict]):  # ### NEW
            outs = []  # ### NEW
            for item in batch:  # ### NEW
                text, stats = prov.query(  # ### NEW
                    item.get("question", ""),  # ### NEW
                    item.get("context", ""),  # ### NEW
                )  # ### NEW
                outs.append(
                    {  # ### NEW
                        "text": text,  # ### NEW
                        "stats": stats,  # ### NEW
                        "cache_hit": bool(
                            (stats or {}).get("cache_hit", False)
                        ),  # ### NEW
                    }
                )  # ### NEW
            return outs  # ### NEW

        batcher = AsyncMicroBatcher(  # ### NEW
            forward_fn,  # ### NEW
            max_batch=8,  # ### NEW
            max_latency_ms=5,  # ### NEW
            name=f"fallback:{system_name}",  # ### NEW
        )  # ### NEW

        asyncio.get_event_loop().create_task(batcher.start())  # ### NEW

        # Register for telemetry too                             # ### NEW
        manager.batchers = getattr(manager, "batchers", {})  # ### NEW
        manager.batchers[batcher.name] = batcher  # ### NEW

        self._cache[system_name] = batcher  # ### NEW
        return batcher  # ### NEW


_fallback_batchers = _FallbackBatcherPool()  # ### NEW


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
    sources: Optional[List[Dict[str, Any]]] = None


# ---- helpers ----
def _find_task(task_id: str) -> Any | None:
    # ... unchanged ...
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
    # ... unchanged ...
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


def _mk_resp(text: Any, stats: Optional[dict]) -> QueryResponse:
    s = dict(stats or {})
    src = s.get("sources") or s.get("docs") or s.get("citations")
    if isinstance(src, dict):
        src = [src]
    if src is not None and not isinstance(src, list):
        src = None
    return QueryResponse(
        text=str(text or ""),
        stats=s,
        cache_hit=bool(s.get("cache_hit", False)),
        sources=src,
    )


# ---- route ----
@router.post("/query", response_model=QueryResponse)
async def orchestrator_query(inp: QueryRequest):
    task = _find_task(inp.task_id)

    # A) Agent path first
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
                    if isinstance(out, tuple) and len(out) == 2:
                        text, stats = out
                        return _mk_resp(text, stats)
                    if isinstance(out, dict) and "text" in out:
                        return _mk_resp(out.get("text"), out.get("stats", {}))
                    return _mk_resp(out, {})
                except Exception as e:
                    agent_err = e
                    break

    # B) Fallback — now uses a batcher instead of direct provider
    system = (
        inp.system
        or (_extract_system_from_task(task) if task is not None else None)
        or "TestSystem"
    )
    try:
        fb = _fallback_batchers.get(system)  # ### NEW
        out = await fb.submit(
            {"question": inp.question, "context": inp.context or ""}
        )  # ### NEW
        if isinstance(out, tuple) and len(out) == 2:  # ### NEW
            text, stats = out  # ### NEW
            return _mk_resp(text, stats)  # ### NEW
        if isinstance(out, dict) and "text" in out:  # ### NEW
            return _mk_resp(out.get("text"), out.get("stats", {}))  # ### NEW
        return _mk_resp(out, {})  # ### NEW
    except Exception as e:
        detail = (
            f"Agent path failed: {agent_err}" if agent_err else "Agent path unavailable"
        )
        raise HTTPException(
            status_code=500, detail=f"{detail}; provider fallback failed: {e}"
        )
