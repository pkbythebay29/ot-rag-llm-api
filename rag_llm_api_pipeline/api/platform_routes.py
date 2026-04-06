from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from rag_llm_api_pipeline.core import audit
from rag_llm_api_pipeline.core.security import validate_api_key_header
from rag_llm_api_pipeline.core.system_metadata import get_system_metadata
from rag_llm_api_pipeline.db import review_store

router = APIRouter(tags=["Platform"])


@router.get(
    "/system/metadata",
    summary="Get system metadata",
    description="Return Krionis platform metadata including version, GAMP classification, and model/prompt placeholders.",
)
def get_metadata() -> dict[str, Any]:
    return get_system_metadata()


@router.get(
    "/review/{review_id}",
    summary="Get a review item",
    description="Retrieve a specific HITL review item, including original response, reviewer notes, and final response if available.",
)
def get_review_item(
    review_id: str,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    item = review_store.get_review(review_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item '{review_id}' was not found.",
        )
    return item


@router.get(
    "/audit/traces/{trace_id}",
    summary="Get trace audit events",
    description="Return append-only audit events associated with a single query trace ID.",
)
def get_trace_audit_events(
    trace_id: str,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    events = audit.get_trace_events(trace_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit events found for trace '{trace_id}'.",
        )
    return {"trace_id": trace_id, "events": events}


@router.get(
    "/audit/reviews/{review_id}",
    summary="Get review audit events",
    description="Return append-only audit events associated with a review ID, including approval or rejection decisions.",
)
def get_review_audit_events(
    review_id: str,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    events = audit.get_review_events(review_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit events found for review '{review_id}'.",
        )
    return {"review_id": review_id, "events": events}
