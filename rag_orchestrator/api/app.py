from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .routes import router as orchestrator_router

app = FastAPI(title="RAG Orchestrator", version="0.1.0")
app.include_router(orchestrator_router, prefix="")

web_dir = Path(__file__).parent.parent / "web"
app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")