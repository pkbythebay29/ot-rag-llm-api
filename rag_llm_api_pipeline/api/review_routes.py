from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from rag_llm_api_pipeline.core import audit, feedback
from rag_llm_api_pipeline.core.compliance import infer_assessment_status
from rag_llm_api_pipeline.core.hitl import (
    create_signoff_payload_examples,
    utc_now_iso,
)
from rag_llm_api_pipeline.core.security import get_user_id, validate_api_key_header
from rag_llm_api_pipeline.db import compliance_store, review_store

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


def _sync_compliance_assessment(item: dict[str, Any]) -> None:
    assessment_id = item.get("assessment_id")
    if not assessment_id:
        return

    assessment = compliance_store.get_assessment(str(assessment_id))
    if not assessment:
        return

    assessment["status"] = item.get("status", assessment.get("status"))
    assessment["review_id"] = item.get("id", assessment.get("review_id"))
    assessment["generated_response"] = item.get("final_response") or item.get(
        "response", assessment.get("generated_response")
    )
    assessment["response_preview"] = item.get(
        "response_preview", assessment.get("response_preview")
    )
    assessment["reviewer_notes"] = item.get("reviewer_notes")
    assessment["reviewer_id"] = item.get("reviewer_id")
    assessment["assessment_status"] = infer_assessment_status(
        str(
            assessment.get("generated_response")
            or assessment.get("response_preview")
            or ""
        )
    )
    assessment.setdefault("timestamps", {})
    assessment["timestamps"]["updated_at"] = utc_now_iso()
    assessment["timestamps"]["reviewed_at"] = item.get("timestamps", {}).get(
        "reviewed_at"
    )
    compliance_store.update_assessment(str(assessment_id), assessment)


@router.get("/pending")
def get_pending_reviews(_: str = Depends(validate_api_key_header)) -> dict[str, Any]:
    items = []
    for item in review_store.get_pending_reviews():
        payload = dict(item)
        payload["signoff_path"] = f"/review/{item['id']}/signoff"
        items.append(payload)
    return {"items": items}


@router.get("/{review_id}/signoff")
def get_review_signoff(
    review_id: str,
    request: Request,
    _: str = Depends(validate_api_key_header),
) -> dict[str, Any]:
    item = _get_review_or_404(review_id)
    base_url = str(request.base_url).rstrip("/")
    return {
        "review_id": review_id,
        "status": item.get("status"),
        "instructions": (
            "Approve by posting the reviewer notes and optional edited final response. "
            "Reject by posting reviewer notes that explain why the draft cannot be released."
        ),
        "signoff_examples": create_signoff_payload_examples(
            review_id,
            base_url=base_url,
            final_response=item.get("response") or "Approved response text.",
        ),
    }


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
    _sync_compliance_assessment(updated_item)
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
    _sync_compliance_assessment(updated_item)
    return updated_item
