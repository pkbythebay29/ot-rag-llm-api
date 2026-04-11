from __future__ import annotations

import json
import os
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.hitl import utc_now_iso
from rag_llm_api_pipeline.core.system_metadata import get_system_metadata

DEFAULT_AUDIT_LOG_PATH = os.path.join("data", "audit", "audit_log.jsonl")


def get_audit_log_path() -> str:
    config = load_config() or {}
    audit_cfg = config.get("audit", {})
    return os.getenv("KRIONIS_AUDIT_LOG_PATH") or audit_cfg.get(
        "log_path", DEFAULT_AUDIT_LOG_PATH
    )


def append_audit_record(record: dict[str, Any]) -> dict[str, Any]:
    path = get_audit_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "recorded_at": utc_now_iso(),
        "system_metadata": get_system_metadata(),
        **record,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
    return payload


def get_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    path = get_audit_log_path()
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    events = [json.loads(line) for line in lines if line.strip()]
    return events[-limit:]


def get_trace_events(trace_id: str) -> list[dict[str, Any]]:
    return [
        event
        for event in get_audit_events(limit=5000)
        if event.get("trace_id") == trace_id
    ]


def get_review_events(review_id: str) -> list[dict[str, Any]]:
    return [
        event
        for event in get_audit_events(limit=5000)
        if event.get("review_id") == review_id
    ]


def log_query_event(
    *,
    trace_id: str,
    system_id: str,
    query: str,
    generated_response: str,
    final_response: str | None,
    retrieved_documents: list[dict[str, Any]],
    user_id: str,
    model_version: str,
    prompt_version: str,
    status: str,
    reviewer_decision: str | None,
    review_id: str | None,
    execution_trace: dict[str, Any],
    sources: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "event_type": "query",
        "trace_id": trace_id,
        "system_id": system_id,
        "query": query,
        "retrieved_documents": retrieved_documents,
        "retrieved_chunks": sources or [],
        "generated_response": generated_response,
        "final_approved_response": final_response,
        "reviewer_decision": reviewer_decision,
        "review_id": review_id,
        "user_id": user_id,
        "reviewer_id": None,
        "status": status,
        "model_version": model_version,
        "prompt_version": prompt_version,
        "execution_trace": execution_trace,
    }
    if extra_fields:
        payload.update(extra_fields)
    return append_audit_record(payload)


def log_review_event(
    *,
    trace_id: str | None,
    review_id: str,
    system_id: str | None,
    query: str,
    generated_response: str,
    final_response: str | None,
    retrieved_documents: list[dict[str, Any]],
    user_id: str | None,
    reviewer_id: str,
    reviewer_notes: str | None,
    status: str,
    model_version: str,
    prompt_version: str,
    execution_trace: dict[str, Any],
) -> dict[str, Any]:
    return append_audit_record(
        {
            "event_type": "review_decision",
            "trace_id": trace_id,
            "review_id": review_id,
            "system_id": system_id,
            "query": query,
            "retrieved_documents": retrieved_documents,
            "generated_response": generated_response,
            "final_approved_response": final_response,
            "reviewer_decision": status,
            "user_id": user_id,
            "reviewer_notes": reviewer_notes,
            "reviewer_id": reviewer_id,
            "status": status,
            "model_version": model_version,
            "prompt_version": prompt_version,
            "execution_trace": execution_trace,
        }
    )
