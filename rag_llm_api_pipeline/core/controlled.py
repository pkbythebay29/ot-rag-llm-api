from __future__ import annotations

import os
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core import audit
from rag_llm_api_pipeline.core.hitl import (
    create_review_item,
    get_response_preview_chars,
    get_version_placeholders,
    requires_human_review,
    utc_now_iso,
)
from rag_llm_api_pipeline.core.model_selection import (
    resolve_runtime_selection,
    summarize_runtime,
)
from rag_llm_api_pipeline.core.orchestrator import get_orchestrator
from rag_llm_api_pipeline.core.platform_state import record_query_route
from rag_llm_api_pipeline.core.query_worker import run_query_in_worker
from rag_llm_api_pipeline.db import review_store


def build_trace(trace_id: str, status: str, stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "status": status,
        "steps": [
            {"stage": "query_received", "timestamp": utc_now_iso()},
            {"stage": "document_search_completed", "timestamp": utc_now_iso()},
            {"stage": "hitl_evaluated", "timestamp": utc_now_iso()},
        ],
        "stats": stats,
    }


def format_stats(stats: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    show_qt = cfg.get("settings", {}).get("show_query_time", True)
    show_ts = cfg.get("settings", {}).get("show_token_speed", True)
    show_ct = cfg.get("settings", {}).get("show_chunk_timing", True)

    if not isinstance(stats, dict) or not (show_qt or show_ts or show_ct):
        return {}

    formatted: dict[str, Any] = {}
    if show_qt and "query_time_sec" in stats:
        formatted["query_time_sec"] = stats["query_time_sec"]
    if show_ts and "tokens_per_sec" in stats:
        formatted.update(
            {
                "gen_time_sec": stats.get("gen_time_sec"),
                "gen_tokens": stats.get("gen_tokens"),
                "tokens_per_sec": stats.get("tokens_per_sec"),
            }
        )
    if show_ct and "retrieval" in stats:
        formatted["retrieval"] = stats.get("retrieval", {})
        formatted["chunks_meta"] = stats.get("chunks_meta", [])
    return formatted


def normalize_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return dict(result.model_dump())
    if isinstance(result, dict):
        return dict(result)
    return {"answer": str(result or "")}


def execute_query(system_id: str, question: str) -> dict[str, Any]:
    if os.getenv("KRIONIS_DISABLE_QUERY_WORKER", "").strip() == "1":
        return normalize_result(
            get_orchestrator().run_query(system_name=system_id, question=question)
        )
    return normalize_result(run_query_in_worker(system_id, question))


def _resolve_runtime(
    system_id: str, runtime_selection: dict[str, Any] | None
) -> dict[str, Any]:
    return resolve_runtime_selection(
        system_name=system_id,
        overrides=runtime_selection,
    )


def execute_query_with_runtime(
    system_id: str,
    question: str,
    runtime_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_runtime = _resolve_runtime(system_id, runtime_selection)
    if os.getenv("KRIONIS_DISABLE_QUERY_WORKER", "").strip() == "1":
        return normalize_result(
            get_orchestrator().run_query(
                system_name=system_id,
                question=question,
                model_selection=resolved_runtime,
            )
        )
    return normalize_result(
        run_query_in_worker(
            system_id,
            question,
            runtime_selection=resolved_runtime,
        )
    )


def build_controlled_response(
    *,
    system_id: str,
    question: str,
    result: Any,
    user_id: str,
    trace_id: str,
    route_name: str,
    agent_task_id: str | None = None,
    extra_review_fields: dict[str, Any] | None = None,
    extra_response_fields: dict[str, Any] | None = None,
    extra_route_fields: dict[str, Any] | None = None,
    audit_context: dict[str, Any] | None = None,
    runtime_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = load_config()
    resolved_runtime = _resolve_runtime(system_id, runtime_selection)
    model_version, prompt_version = get_version_placeholders(resolved_runtime)
    normalized = normalize_result(result)
    answer = str(
        normalized.get("answer")
        or normalized.get("text")
        or normalized.get("response")
        or ""
    )
    sources = list(normalized.get("sources") or [])
    stats = dict(normalized.get("stats") or {})
    retrieved_documents = list(normalized.get("retrieved_documents") or [])
    formatted_stats = format_stats(stats, cfg)
    trace = build_trace(trace_id, "evaluated", formatted_stats)
    trace["runtime"] = summarize_runtime(resolved_runtime)
    trace["steps"].insert(
        1,
        {
            "stage": f"{route_name}_executed",
            "timestamp": utc_now_iso(),
            "agent_task_id": agent_task_id,
        },
    )

    route_payload = {
        "timestamp": utc_now_iso(),
        "trace_id": trace_id,
        "route_name": route_name,
        "system": system_id,
        "question": question,
        "question_preview": question[:120],
        "agent_task_id": agent_task_id,
        "runtime": summarize_runtime(resolved_runtime),
        **(extra_route_fields or {}),
    }
    audit_fields = {"route_name": route_name, **(audit_context or {})}
    if agent_task_id:
        audit_fields["agent_task_id"] = agent_task_id
    audit_fields["runtime"] = summarize_runtime(resolved_runtime)

    if requires_human_review(question, answer):
        review_item = create_review_item(
            question,
            answer,
            system_id=system_id,
            user_id=user_id,
            trace_id=trace_id,
            retrieved_documents=retrieved_documents,
            response_preview=answer[: get_response_preview_chars()],
            runtime_selection=resolved_runtime,
        )
        if agent_task_id:
            review_item["agent_task_id"] = agent_task_id
        if extra_review_fields:
            review_item.update(extra_review_fields)
        review_store.save_review(review_item)
        trace["steps"].append({"stage": "review_queued", "timestamp": utc_now_iso()})
        audit.log_query_event(
            trace_id=trace_id,
            system_id=system_id,
            query=question,
            generated_response=answer,
            final_response=None,
            retrieved_documents=retrieved_documents,
            user_id=user_id,
            model_version=model_version,
            prompt_version=prompt_version,
            status="pending_review",
            reviewer_decision="pending_review",
            review_id=review_item["id"],
            execution_trace=trace,
            sources=sources,
            extra_fields=audit_fields,
        )
        response: dict[str, Any] = {
            "status": "pending_review",
            "trace_id": trace_id,
            "review_id": review_item["id"],
            "system": system_id,
            "question": question,
            "response_preview": review_item["response_preview"],
            "runtime": summarize_runtime(resolved_runtime),
        }
        if agent_task_id:
            response["agent_task_id"] = agent_task_id
        if formatted_stats:
            response["stats"] = formatted_stats
        if extra_response_fields:
            response.update(extra_response_fields)
        record_query_route(
            {
                **route_payload,
                "status": "pending_review",
                "review_id": review_item["id"],
            }
        )
        return response

    trace["steps"].append({"stage": "auto_approved", "timestamp": utc_now_iso()})
    audit.log_query_event(
        trace_id=trace_id,
        system_id=system_id,
        query=question,
        generated_response=answer,
        final_response=answer,
        retrieved_documents=retrieved_documents,
        user_id=user_id,
        model_version=model_version,
        prompt_version=prompt_version,
        status="approved",
        reviewer_decision="auto_approved",
        review_id=None,
        execution_trace=trace,
        sources=sources,
        extra_fields=audit_fields,
    )
    response = {
        "status": "approved",
        "trace_id": trace_id,
        "system": system_id,
        "question": question,
        "answer": answer,
        "sources": sources,
        "runtime": summarize_runtime(resolved_runtime),
    }
    if agent_task_id:
        response["agent_task_id"] = agent_task_id
    if formatted_stats:
        response["stats"] = formatted_stats
    if extra_response_fields:
        response.update(extra_response_fields)
    record_query_route(
        {
            **route_payload,
            "status": "approved",
            "review_id": None,
        }
    )
    return response
