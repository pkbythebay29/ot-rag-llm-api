from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import router as orchestrator_router
from .imports import load_builtin_agents
from . import routes_telemetry 
from . import routes_query

load_builtin_agents() 
 
app = FastAPI(title="RAG Orchestrator", version="0.1.0")

# CORS for local UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# >>> IMPORTANT: API under /orchestrator <<<
app.include_router(orchestrator_router, prefix="/orchestrator")
app.include_router(routes_query.router)
app.include_router(routes_telemetry.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}

# Static UI last (so /orchestrator/* still hits API)
web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
