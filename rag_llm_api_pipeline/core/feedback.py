from __future__ import annotations

import json
import os
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.hitl import utc_now_iso

DEFAULT_FEEDBACK_LOG_PATH = os.path.join("data", "feedback", "corrections.jsonl")


def get_feedback_log_path() -> str:
    config = load_config() or {}
    feedback_cfg = config.get("feedback", {})
    return os.getenv("KRIONIS_FEEDBACK_LOG_PATH") or feedback_cfg.get(
        "corrections_path", DEFAULT_FEEDBACK_LOG_PATH
    )


def record_review_feedback(item: dict[str, Any]) -> dict[str, Any]:
    path = get_feedback_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "recorded_at": utc_now_iso(),
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
    return payload
