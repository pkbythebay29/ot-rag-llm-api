from fastapi import APIRouter
from .routes_agents import router as agents_router
from .routes_catalog import router as catalog_router
from .routes_query import router as query_router 

# optional telemetry (safe if pool absent)
try:
    from ..runtime.batcher_pool import BatcherPool
except Exception:
    BatcherPool = None  # type: ignore

router = APIRouter()
router.include_router(agents_router)
router.include_router(catalog_router)
router.include_router(query_router)  

# ---- diagnostics
try:
    from ..agents.registry import list_registered  # type: ignore
except Exception:
    def list_registered(): return []

@router.get("/diag/agents", tags=["diagnostics"])
async def diag_agents():
    return {"registered": list_registered()}

telemetry_router = APIRouter(prefix="/telemetry", tags=["telemetry"])

def _iter_batchers():
    items = {}
    try:
        if BatcherPool and hasattr(BatcherPool, "instances"):
            return {str(k): v for k, v in BatcherPool.instances().items()}  # type: ignore
    except Exception:
        pass
    try:
        if BatcherPool and hasattr(BatcherPool, "_batchers"):
            return {str(k): v for k, v in getattr(BatcherPool, "_batchers").items()}
    except Exception:
        pass
    return items

@telemetry_router.get("/batching")
async def batching_stats():
    stats = {}
    for key, batcher in _iter_batchers().items():
        try:
            stats[key] = batcher.stats()
        except Exception as e:
            stats[key] = {"error": str(e)}
    return {"batching": stats}

router.include_router(telemetry_router)

# --- diagnostics (add at bottom of routes.py) ---
from fastapi.responses import JSONResponse
from ._state import manager
from ..agents.base import AgentSpec

@router.post("/diag/smoke-start", tags=["diagnostics"])
async def smoke_start(system: str = "TestSystem", agent: str = "retriever", prefix: str = "smoke"):
    try:
        h = await manager.create(agent, AgentSpec(name=f"{prefix}-{agent}", system=system, tenant="default"))
        return {"ok": True, "task_id": str(getattr(h, "id", ""))}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=400, content={"ok": False, "detail": str(e), "trace": traceback.format_exc()})

# If your provider pool exposes resolve_system_yaml and RagLLMApiProvider, wire a direct probe:
try:
    from .config_bridge import resolve_system_yaml  # your existing helper
    from ..providers.rag_llm_api_provider import RagLLMApiProvider
except Exception:
    resolve_system_yaml = None
    RagLLMApiProvider = None

@router.get("/diag/provider", tags=["diagnostics"])
async def diag_provider(system: str = "TestSystem"):
    if not (resolve_system_yaml and RagLLMApiProvider):
        return JSONResponse(status_code=501, content={"ok": False, "detail": "provider diag not wired"})
    try:
        path = resolve_system_yaml(system)
        prov = RagLLMApiProvider(path)
        # trivial call to ensure wrapper shapes are ok (no side effects)
        _ = hasattr(prov, "query")
        return {"ok": True, "system_yaml": path}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=400, content={"ok": False, "detail": str(e), "trace": traceback.format_exc()})


