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


def get_version_placeholders() -> tuple[str, str]:
    config = load_config() or {}
    hitl_cfg = config.get("hitl", {})
    llm_cfg = config.get("llm", {})
    model_cfg = config.get("models", {})
    model_version = str(
        hitl_cfg.get("model_version")
        or model_cfg.get("llm_model")
        or "model-version-placeholder"
    )
    prompt_version = str(
        hitl_cfg.get("prompt_version")
        or llm_cfg.get("prompt_version")
        or "prompt-version-placeholder"
    )
    return model_version, prompt_version


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


def create_review_item(
    query: str,
    response: str,
    *,
    system_id: str | None = None,
    user_id: str = "anonymous",
    trace_id: str | None = None,
    retrieved_documents: list[dict[str, Any]] | None = None,
    response_preview: str | None = None,
) -> dict[str, Any]:
    created_at = utc_now_iso()
    model_version, prompt_version = get_version_placeholders()
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
    }
