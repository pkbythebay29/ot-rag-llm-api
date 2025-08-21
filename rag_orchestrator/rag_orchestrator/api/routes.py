from fastapi import APIRouter
from .routes_agents import router as agents_router
from .routes_catalog import router as catalog_router

# optional telemetry (safe if pool absent)
try:
    from ..runtime.batcher_pool import BatcherPool
except Exception:
    BatcherPool = None  # type: ignore

router = APIRouter()
router.include_router(agents_router)
router.include_router(catalog_router)

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
