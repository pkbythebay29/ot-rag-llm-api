from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Header, Request
from fastapi.templating import Jinja2Templates

from rag_llm_api_pipeline.core.security import get_configured_api_key
from rag_llm_api_pipeline.db import review_store

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
router = APIRouter(prefix="/ui", tags=["UI"])


@router.get("/reviews")
def review_dashboard(
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    configured_key = get_configured_api_key()
    is_authorized = bool(configured_key) and x_api_key == configured_key
    pending_reviews = review_store.get_pending_reviews() if is_authorized else []
    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "authorized": is_authorized,
            "pending_reviews": pending_reviews,
        },
    )
