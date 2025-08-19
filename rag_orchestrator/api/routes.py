from fastapi import APIRouter
from .routes_agents import router as agents_router
from .routes_catalog import router as catalog_router

router = APIRouter()
router.include_router(agents_router)
router.include_router(catalog_router)