from __future__ import annotations

import json
import os
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.hitl import utc_now_iso
from rag_llm_api_pipeline.db import metadata_store

DEFAULT_FEEDBACK_LOG_PATH = os.path.join("data", "feedback", "corrections.jsonl")
DEFAULT_QUALITY_LOG_PATH = os.path.join("data", "feedback", "quality_ratings.jsonl")


def get_feedback_log_path() -> str:
    config = load_config() or {}
    feedback_cfg = config.get("feedback", {})
    return os.getenv("KRIONIS_FEEDBACK_LOG_PATH") or feedback_cfg.get(
        "corrections_path", DEFAULT_FEEDBACK_LOG_PATH
    )


def record_review_feedback(item: dict[str, Any]) -> dict[str, Any]:
    path = get_feedback_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    recorded_at = utc_now_iso()
    payload = {
        "recorded_at": recorded_at,
        "review_id": item.get("id"),
        "trace_id": item.get("trace_id"),
        "system_id": item.get("system_id"),
        "query": item.get("query"),
        "original_response": item.get("response"),
        "final_response": item.get("final_response"),
        "status": item.get("status"),
        "reviewer_id": item.get("reviewer_id"),
        "reviewer_notes": item.get("reviewer_notes"),
        "model_version": item.get("model_version"),
        "prompt_version": item.get("prompt_version"),
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
    metadata_store.save_record(
        event_type="review_feedback",
        created_at=recorded_at,
        payload=payload,
        trace_id=payload.get("trace_id"),
        review_id=payload.get("review_id"),
        status=payload.get("status"),
        system_id=payload.get("system_id"),
        user_id=payload.get("reviewer_id"),
        reviewer_id=payload.get("reviewer_id"),
    )
    return payload


def get_quality_log_path() -> str:
    config = load_config() or {}
    feedback_cfg = config.get("feedback", {})
    return os.getenv("KRIONIS_QUALITY_LOG_PATH") or feedback_cfg.get(
        "quality_path", DEFAULT_QUALITY_LOG_PATH
    )


def record_quality_feedback(
    *,
    trace_id: str,
    rating: str,
    system_id: str | None,
    query: str | None,
    response: str | None,
    review_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    path = get_quality_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    recorded_at = utc_now_iso()
    payload = {
        "recorded_at": recorded_at,
        "trace_id": trace_id,
        "review_id": review_id,
        "rating": rating,
        "system_id": system_id,
        "query": query,
        "response": response,
        "user_id": user_id,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
    metadata_store.save_record(
        event_type="quality_feedback",
        created_at=recorded_at,
        payload=payload,
        trace_id=payload.get("trace_id"),
        review_id=payload.get("review_id"),
        rating=payload.get("rating"),
        system_id=payload.get("system_id"),
        user_id=payload.get("user_id"),
    )
    return payload
