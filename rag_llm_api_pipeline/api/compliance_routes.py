from __future__ import annotations

import os
import sys
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from rag_llm_api_pipeline.config_loader import resolve_runtime_path
from rag_llm_api_pipeline.core import audit
from rag_llm_api_pipeline.core.compliance import (
    build_compliance_question,
    get_audit_excerpt_chars,
    infer_assessment_status,
    resolve_document_text,
    resolve_regulation_system,
    summarize_document_text,
)
from rag_llm_api_pipeline.core.controlled import (
    build_controlled_response,
    execute_query,
)
from rag_llm_api_pipeline.core.hitl import utc_now_iso
from rag_llm_api_pipeline.core.index_admin import get_index_status
from rag_llm_api_pipeline.core.index_worker import rebuild_index_in_worker
from rag_llm_api_pipeline.core.security import get_user_id
from rag_llm_api_pipeline.db import compliance_store, regulation_pool_store

router = APIRouter(prefix="/compliance", tags=["Compliance"])


class ComplianceAssessmentRequest(BaseModel):
    document_name: str = Field(
        ...,
        description="Human-readable name of the regulated document under assessment.",
    )
    document_text: str | None = Field(
        default=None,
        description="Inline regulated document text to assess.",
    )
    document_path: str | None = Field(
        default=None,
        description="Optional local file path, absolute or relative to settings.data_dir.",
    )
    regulation_system: str | None = Field(
        default=None,
        description="System containing the indexed regulation corpus to compare against.",
    )
    framework: str | None = Field(
        default=None,
        description="Optional framework, jurisdiction, or quality system label.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional focus area such as validation, change control, or data integrity.",
    )


class RegulationPoolRequest(BaseModel):
    name: str = Field(..., description="Stable system name for the regulation pool.")
    docs_dir: str = Field(
        ...,
        description="Directory containing regulation-only source documents.",
    )
    docs: list[str] | None = Field(
        default=None,
        description="Optional explicit filenames inside docs_dir.",
    )
    description: str | None = Field(
        default=None,
        description="Optional operator-facing description of the regulation pool.",
    )
    framework: str | None = Field(
        default=None,
        description="Optional framework or jurisdiction label for the pool.",
    )
    focus: str | None = Field(
        default=None,
        description="Optional focus label such as GMP, validation, or data integrity.",
    )


def _ensure_orchestrator_import_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    orchestrator_root = os.path.join(repo_root, "rag_orchestrator")
    if os.path.isdir(orchestrator_root) and orchestrator_root not in sys.path:
        sys.path.insert(0, orchestrator_root)


def _build_assessment_record(
    *,
    assessment_id: str,
    regulation_system: str,
    payload: ComplianceAssessmentRequest,
    resolved_document_path: str | None,
    document_text: str,
    compliance_question: str,
    response: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    now = utc_now_iso()
    answer_text = str(response.get("answer") or response.get("response_preview") or "")
    return {
        "id": assessment_id,
        "assessment_type": "regulated_document_compliance",
        "status": response.get("status", "unknown"),
        "assessment_status": infer_assessment_status(answer_text),
        "system_id": regulation_system,
        "regulation_system": regulation_system,
        "trace_id": response.get("trace_id"),
        "review_id": response.get("review_id"),
        "user_id": user_id,
        "document_name": payload.document_name,
        "document_path": resolved_document_path,
        "document_text_excerpt": summarize_document_text(
            document_text, limit=get_audit_excerpt_chars()
        ),
        "document_length_chars": len(document_text),
        "framework": payload.framework,
        "focus": payload.focus,
        "query": compliance_question,
        "generated_response": response.get("answer"),
        "response_preview": response.get("response_preview"),
        "sources": response.get("sources", []),
        "timestamps": {
            "created_at": now,
            "updated_at": now,
        },
    }


def _serialize_pool(item: dict[str, Any]) -> dict[str, Any]:
    try:
        status = get_index_status(str(item["name"]))
    except ValueError:
        status = None
    return {
        **item,
        "agent_type": "regulatory",
        "index_status": status,
    }


@router.post(
    "/assess",
    summary="Assess a regulated document for compliance",
    description=(
        "Submit a regulated document as inline text or a local file path, compare it "
        "against an indexed regulation corpus, and send the generated assessment "
        "through the normal Krionis HITL and audit chain."
    ),
)
def assess_document(
    payload: ComplianceAssessmentRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = get_user_id(x_user_id, default="anonymous")
    trace_id = str(uuid4())
    assessment_id = str(uuid4())

    try:
        document_text, resolved_document_path = resolve_document_text(
            document_text=payload.document_text,
            document_path=payload.document_path,
        )
        regulation_system = resolve_regulation_system(payload.regulation_system)
        compliance_question = build_compliance_question(
            document_name=payload.document_name,
            document_text=document_text,
            framework=payload.framework,
            focus=payload.focus,
        )
        result = execute_query(regulation_system, compliance_question)
        response = build_controlled_response(
            system_id=regulation_system,
            question=compliance_question,
            result=result,
            user_id=user_id,
            trace_id=trace_id,
            route_name="compliance_assessment",
            extra_review_fields={
                "assessment_id": assessment_id,
                "assessment_type": "regulated_document_compliance",
            },
            extra_response_fields={
                "assessment_id": assessment_id,
                "document_name": payload.document_name,
                "regulation_system": regulation_system,
                "framework": payload.framework,
                "focus": payload.focus,
            },
            extra_route_fields={
                "assessment_id": assessment_id,
                "document_name": payload.document_name,
            },
            audit_context={
                "assessment_id": assessment_id,
                "document_name": payload.document_name,
                "document_path": resolved_document_path,
                "framework": payload.framework,
                "focus": payload.focus,
            },
        )
        assessment = _build_assessment_record(
            assessment_id=assessment_id,
            regulation_system=regulation_system,
            payload=payload,
            resolved_document_path=resolved_document_path,
            document_text=document_text,
            compliance_question=compliance_question,
            response=response,
            user_id=user_id,
        )
        compliance_store.save_assessment(assessment)
        audit.append_audit_record(
            {
                "event_type": "compliance_assessment",
                "assessment_id": assessment_id,
                "trace_id": response.get("trace_id"),
                "review_id": response.get("review_id"),
                "system_id": regulation_system,
                "user_id": user_id,
                "status": assessment["status"],
                "assessment_status": assessment["assessment_status"],
                "document_name": payload.document_name,
                "document_path": resolved_document_path,
                "framework": payload.framework,
                "focus": payload.focus,
                "document_length_chars": len(document_text),
                "document_excerpt": assessment["document_text_excerpt"],
            }
        )
        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/pools",
    summary="List regulation-only data pools",
    description="Return dedicated regulation corpora that can be indexed and used by the built-in regulatory agent.",
)
def list_regulation_pools_route() -> dict[str, Any]:
    items = [_serialize_pool(pool) for pool in regulation_pool_store.list_pools()]
    return {
        "items": items,
        "database_path": regulation_pool_store.get_db_path(),
        "default_regulatory_agent_type": "regulatory",
    }


@router.post(
    "/pools",
    summary="Create or update one regulation-only data pool",
    description="Register a dedicated corpus of regulatory documents so Krionis can expose it as a compliance-ready system.",
)
def create_regulation_pool(payload: RegulationPoolRequest) -> dict[str, Any]:
    docs_dir = resolve_runtime_path(payload.docs_dir) or payload.docs_dir
    if not docs_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="docs_dir is required.",
        )
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required.",
        )
    os.makedirs(docs_dir, exist_ok=True)
    existing = regulation_pool_store.get_pool(name)
    created_at = (
        existing.get("timestamps", {}).get("created_at") if existing else utc_now_iso()
    )
    pool = {
        "name": name,
        "docs_dir": docs_dir,
        "docs": list(payload.docs or []),
        "description": payload.description,
        "framework": payload.framework,
        "focus": payload.focus,
        "timestamps": {
            "created_at": created_at,
            "updated_at": utc_now_iso(),
        },
    }
    saved = regulation_pool_store.save_pool(pool)
    return _serialize_pool(saved)


@router.get(
    "/pools/{pool_name}",
    summary="Get one regulation-only data pool",
    description="Return a dedicated regulation pool with index status and regulatory agent compatibility.",
)
def get_regulation_pool(pool_name: str) -> dict[str, Any]:
    item = regulation_pool_store.get_pool(pool_name)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulation pool '{pool_name}' was not found.",
        )
    return _serialize_pool(item)


@router.post(
    "/pools/{pool_name}/rebuild",
    summary="Rebuild one regulation-only data pool",
    description="Rebuild the retrieval cache for a dedicated regulation corpus.",
)
def rebuild_regulation_pool(pool_name: str) -> dict[str, Any]:
    item = regulation_pool_store.get_pool(pool_name)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulation pool '{pool_name}' was not found.",
        )
    try:
        report = rebuild_index_in_worker(pool_name)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return {
        "pool": _serialize_pool(item),
        "status": "rebuilt",
        "report": report,
        "agent_type": "regulatory",
    }


@router.post(
    "/pools/{pool_name}/start-agent",
    summary="Start one regulatory agent",
    description="Start the built-in regulatory agent bound to a dedicated regulation pool.",
)
async def start_regulatory_agent(pool_name: str) -> dict[str, Any]:
    item = regulation_pool_store.get_pool(pool_name)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulation pool '{pool_name}' was not found.",
        )

    try:
        _ensure_orchestrator_import_path()
        from rag_orchestrator.agents.base import AgentSpec
        from rag_orchestrator.agents.registry import list_registered
        from rag_orchestrator.api._state import manager
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if "regulatory" not in list_registered():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Regulatory agent is not registered.",
        )

    handles = getattr(manager, "handles", {}) or {}
    suffix = len(handles) + 1
    spec = AgentSpec(
        name=f"regulatory{suffix}-regulatory-0",
        system=pool_name,
        tenant="default",
    )
    handle = await manager.create("regulatory", spec)
    return {
        "task_id": handle.name,
        "handle_id": handle.id,
        "name": handle.name,
        "agent_type": handle.agent_type,
        "system": handle.system,
        "ready": handle.ready,
        "started_at": utc_now_iso(),
    }


@router.get(
    "/assessments",
    summary="List stored compliance assessments",
    description="Return recent regulated-document compliance assessments stored in the local compliance SQLite database.",
)
def list_compliance_assessments(
    limit: int = 50,
    status_name: str | None = None,
) -> dict[str, Any]:
    return {
        "summary": compliance_store.get_summary(),
        "items": compliance_store.list_assessments(limit=limit, status=status_name),
        "database_path": compliance_store.get_db_path(),
    }


@router.get(
    "/assessments/{assessment_id}",
    summary="Get one compliance assessment",
    description="Return a previously stored compliance assessment by ID.",
)
def get_compliance_assessment(assessment_id: str) -> dict[str, Any]:
    item = compliance_store.get_assessment(assessment_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance assessment '{assessment_id}' was not found.",
        )
    return item
