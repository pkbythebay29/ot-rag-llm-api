from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from rag_llm_api_pipeline.core import audit, feedback
from rag_llm_api_pipeline.core.hitl import utc_now_iso
from rag_llm_api_pipeline.core.security import get_user_id, validate_api_key_header
from rag_llm_api_pipeline.db import review_store

router = APIRouter(prefix="/review", tags=["Review"])


class ApproveReviewRequest(BaseModel):
    final_response: str | None = None
    reviewer_notes: str | None = None


class RejectReviewRequest(BaseModel):
    reviewer_notes: str


def _get_review_or_404(review_id: str) -> dict[str, Any]:
    item = review_store.get_review(review_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item '{review_id}' was not found.",
        )
    return item


def _ensure_pending(item: dict[str, Any]) -> None:
    if item.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review item is no longer pending.",
        )


@router.get("/pending")
def get_pending_reviews(_: str = Depends(validate_api_key_header)) -> dict[str, Any]:
    return {"items": review_store.get_pending_reviews()}


@router.post("/{review_id}/approve")
def approve_review(
    review_id: str,
    payload: ApproveReviewRequest,
    _: str = Depends(validate_api_key_header),
    x_reviewer_id: str | None = Header(default=None),
) -> dict[str, Any]:
    item = _get_review_or_404(review_id)
    _ensure_pending(item)

    reviewer_id = get_user_id(x_reviewer_id, default="reviewer")
    final_response = payload.final_response or item["response"]
    item["status"] = "approved"
    item["reviewer_id"] = reviewer_id
    item["reviewer_notes"] = payload.reviewer_notes
    item["final_response"] = final_response
    item["timestamps"]["reviewed_at"] = utc_now_iso()
    updated_item = review_store.update_review(review_id, item)

    execution_trace = {
        "trace_id": updated_item.get("trace_id"),
        "steps": [
            {"stage": "review_loaded", "timestamp": utc_now_iso()},
            {"stage": "review_approved", "timestamp": utc_now_iso()},
        ],
    }
    audit.log_review_event(
        trace_id=updated_item.get("trace_id"),
        review_id=review_id,
        system_id=updated_item.get("system_id"),
        query=updated_item["query"],
        generated_response=updated_item["response"],
        final_response=updated_item["final_response"],
        retrieved_documents=updated_item.get("retrieved_documents", []),
        user_id=updated_item.get("user_id"),
        reviewer_id=reviewer_id,
        reviewer_notes=updated_item.get("reviewer_notes"),
        status=updated_item["status"],
        model_version=updated_item.get("model_version", "model-version-placeholder"),
        prompt_version=updated_item.get("prompt_version", "prompt-version-placeholder"),
        execution_trace=execution_trace,
    )
    feedback.record_review_feedback(updated_item)
    return updated_item


@router.post("/{review_id}/reject")
def reject_review(
    review_id: str,
    payload: RejectReviewRequest,
    _: str = Depends(validate_api_key_header),
    x_reviewer_id: str | None = Header(default=None),
) -> dict[str, Any]:
    item = _get_review_or_404(review_id)
    _ensure_pending(item)

    reviewer_id = get_user_id(x_reviewer_id, default="reviewer")
    item["status"] = "rejected"
    item["reviewer_id"] = reviewer_id
    item["reviewer_notes"] = payload.reviewer_notes
    item["timestamps"]["reviewed_at"] = utc_now_iso()
    updated_item = review_store.update_review(review_id, item)

    execution_trace = {
        "trace_id": updated_item.get("trace_id"),
        "steps": [
            {"stage": "review_loaded", "timestamp": utc_now_iso()},
            {"stage": "review_rejected", "timestamp": utc_now_iso()},
        ],
    }
    audit.log_review_event(
        trace_id=updated_item.get("trace_id"),
        review_id=review_id,
        system_id=updated_item.get("system_id"),
        query=updated_item["query"],
        generated_response=updated_item["response"],
        final_response=updated_item.get("final_response"),
        retrieved_documents=updated_item.get("retrieved_documents", []),
        user_id=updated_item.get("user_id"),
        reviewer_id=reviewer_id,
        reviewer_notes=updated_item.get("reviewer_notes"),
        status=updated_item["status"],
        model_version=updated_item.get("model_version", "model-version-placeholder"),
        prompt_version=updated_item.get("prompt_version", "prompt-version-placeholder"),
        execution_trace=execution_trace,
    )
    feedback.record_review_feedback(updated_item)
    return updated_item
