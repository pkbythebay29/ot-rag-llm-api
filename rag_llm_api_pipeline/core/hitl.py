from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from rag_llm_api_pipeline.config_loader import load_config

DEFAULT_KEYWORDS = (
    "dosage",
    "treatment",
    "compliance",
    "gmp",
    "validation",
)
DEFAULT_RESPONSE_LENGTH_THRESHOLD = 800
DEFAULT_RESPONSE_PREVIEW_CHARS = 280


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hitl_config() -> dict[str, Any]:
    config = load_config() or {}
    return config.get("hitl", {})


def get_review_keywords() -> tuple[str, ...]:
    cfg_keywords = _hitl_config().get("review_keywords") or DEFAULT_KEYWORDS
    return tuple(str(keyword).strip().lower() for keyword in cfg_keywords if keyword)


def get_response_length_threshold() -> int:
    return int(
        _hitl_config().get(
            "response_length_threshold", DEFAULT_RESPONSE_LENGTH_THRESHOLD
        )
    )


def get_response_preview_chars() -> int:
    return int(
        _hitl_config().get("response_preview_chars", DEFAULT_RESPONSE_PREVIEW_CHARS)
    )


def get_version_placeholders(
    runtime_selection: dict[str, Any] | None = None,
) -> tuple[str, str]:
    config = load_config() or {}
    hitl_cfg = config.get("hitl", {})
    llm_cfg = config.get("llm", {})
    model_cfg = config.get("models", {})
    runtime = runtime_selection or {}
    model_version = str(
        runtime.get("inference_model")
        or runtime.get("llm_model")
        or runtime.get("inference_model_key")
        or runtime.get("runtime_profile")
        or hitl_cfg.get("model_version")
        or model_cfg.get("llm_model")
        or "model-version-placeholder"
    )
    prompt_version = str(
        runtime.get("prompt_version")
        or hitl_cfg.get("prompt_version")
        or llm_cfg.get("prompt_version")
        or "prompt-version-placeholder"
    )
    return model_version, prompt_version


def create_signoff_payload_examples(
    review_id: str,
    *,
    base_url: str,
    reviewer_id: str = "qa-reviewer-1",
    final_response: str = "Approved response text.",
    reviewer_notes: str = "Validated against the current controlled source.",
) -> dict[str, Any]:
    approve_path = f"/review/{review_id}/approve"
    reject_path = f"/review/{review_id}/reject"
    approve_headers = {
        "x-api-key": "<review-api-key>",
        "x-reviewer-id": reviewer_id,
        "content-type": "application/json",
    }
    approve_body = {
        "final_response": final_response,
        "reviewer_notes": reviewer_notes,
    }
    reject_body = {
        "reviewer_notes": "Rejected pending clarification or additional evidence.",
    }
    return {
        "approve": {
            "method": "POST",
            "path": approve_path,
            "url": f"{base_url.rstrip('/')}{approve_path}",
            "headers": approve_headers,
            "body": approve_body,
            "curl": (
                "curl -X POST "
                f"\"{base_url.rstrip('/')}{approve_path}\" "
                "-H \"x-api-key: <review-api-key>\" "
                f"-H \"x-reviewer-id: {reviewer_id}\" "
                "-H \"content-type: application/json\" "
                f"-d '{{\"final_response\":\"{final_response}\",\"reviewer_notes\":\"{reviewer_notes}\"}}'"
            ),
        },
        "reject": {
            "method": "POST",
            "path": reject_path,
            "url": f"{base_url.rstrip('/')}{reject_path}",
            "headers": approve_headers,
            "body": reject_body,
            "curl": (
                "curl -X POST "
                f"\"{base_url.rstrip('/')}{reject_path}\" "
                "-H \"x-api-key: <review-api-key>\" "
                f"-H \"x-reviewer-id: {reviewer_id}\" "
                "-H \"content-type: application/json\" "
                "-d '{\"reviewer_notes\":\"Rejected pending clarification or additional evidence.\"}'"
            ),
        },
    }


def create_review_item(
    query: str,
    response: str,
    *,
    system_id: str | None = None,
    user_id: str = "anonymous",
    trace_id: str | None = None,
    retrieved_documents: list[dict[str, Any]] | None = None,
    response_preview: str | None = None,
    runtime_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    created_at = utc_now_iso()
    model_version, prompt_version = get_version_placeholders(runtime_selection)
    preview = response_preview
    if preview is None:
        preview_limit = get_response_preview_chars()
        preview = (response or "")[:preview_limit]

    return {
        "id": str(uuid4()),
        "system_id": system_id,
        "trace_id": trace_id,
        "query": query,
        "response": response,
        "response_preview": preview,
        "status": "pending",
        "user_id": user_id,
        "reviewer_id": None,
        "reviewer_notes": None,
        "final_response": None,
        "retrieved_documents": retrieved_documents or [],
        "timestamps": {
            "created_at": created_at,
            "updated_at": created_at,
            "reviewed_at": None,
        },
        "model_version": model_version,
        "prompt_version": prompt_version,
        "runtime": dict(runtime_selection or {}),
    }


def requires_human_review(query: str, response: str) -> bool:
    normalized_query = (query or "").lower()
    normalized_response = (response or "").lower()

    keywords = get_review_keywords()
    keyword_match = any(
        keyword in normalized_query or keyword in normalized_response
        for keyword in keywords
    )
    response_too_long = len(response or "") >= get_response_length_threshold()
    return keyword_match or response_too_long
