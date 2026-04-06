from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Header, Request
from fastapi.templating import Jinja2Templates

from rag_llm_api_pipeline.core.security import get_configured_api_key
from rag_llm_api_pipeline.db import review_store

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)
router = APIRouter(prefix="/ui", tags=["UI"])
root_router = APIRouter(tags=["UI"])


@root_router.get("/")
def platform_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="platform_v2.html",
        context={},
    )


@router.get("/telemetry")
def telemetry_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="telemetry.html",
        context={},
    )


@router.get("/runtime")
def runtime_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="runtime.html",
        context={},
    )


@router.get("/configuration")
def configuration_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="configuration.html",
        context={},
    )


@router.get("/records")
def records_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="records.html",
        context={},
    )


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
