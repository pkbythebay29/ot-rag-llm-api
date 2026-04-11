from __future__ import annotations

from pathlib import Path

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.system_assets import list_regulation_pools
from rag_llm_api_pipeline.loader import load_docs

DEFAULT_EXCERPT_CHARS = 4000
DEFAULT_AUDIT_EXCERPT_CHARS = 1200


def _compliance_config() -> dict:
    config = load_config() or {}
    return config.get("compliance", {})


def get_default_regulation_system() -> str:
    cfg = _compliance_config()
    configured = str(cfg.get("default_regulation_system") or "").strip()
    if configured:
        return configured

    pools = list_regulation_pools(load_config() or {})
    if pools:
        return str(pools[0]["name"])

    assets = (load_config() or {}).get("assets") or []
    if assets and isinstance(assets[0], dict) and assets[0].get("name"):
        return str(assets[0]["name"])
    return "TestSystem"


def get_document_excerpt_chars() -> int:
    cfg = _compliance_config()
    return int(cfg.get("document_excerpt_chars", DEFAULT_EXCERPT_CHARS))


def get_audit_excerpt_chars() -> int:
    cfg = _compliance_config()
    return int(cfg.get("audit_excerpt_chars", DEFAULT_AUDIT_EXCERPT_CHARS))


def resolve_regulation_system(value: str | None) -> str:
    provided = str(value or "").strip()
    return provided or get_default_regulation_system()


def resolve_document_text(
    *,
    document_text: str | None,
    document_path: str | None,
) -> tuple[str, str | None]:
    inline_text = str(document_text or "").strip()
    if inline_text:
        return inline_text, None

    candidate = str(document_path or "").strip()
    if not candidate:
        raise ValueError("Provide document_text or document_path.")

    path = Path(candidate).expanduser()
    if not path.is_absolute():
        config = load_config() or {}
        data_dir = Path(
            config.get("settings", {}).get("data_dir", "data/manuals")
        ).expanduser()
        path = data_dir / path

    if not path.exists():
        raise ValueError(f"Document path was not found: {path}")

    pages = [page.strip() for page in load_docs(str(path.resolve())) if page.strip()]
    if not pages:
        raise ValueError(f"No readable text was extracted from: {path}")
    return "\n\n".join(pages), str(path.resolve())


def build_compliance_question(
    *,
    document_name: str,
    document_text: str,
    framework: str | None = None,
    focus: str | None = None,
    excerpt_chars: int | None = None,
) -> str:
    excerpt_limit = excerpt_chars or get_document_excerpt_chars()
    excerpt = summarize_document_text(document_text, limit=excerpt_limit)
    framework_text = str(framework or "").strip() or "General regulated operations"
    focus_text = str(focus or "").strip() or "Overall compliance posture"

    return (
        "Assess the following regulated document for compliance against the indexed "
        "regulation corpus.\n\n"
        "Return a concise assessment with these sections:\n"
        "1. Overall status\n"
        "2. Applicable requirements and observations\n"
        "3. Compliance gaps or missing evidence\n"
        "4. Recommended remediation or next review steps\n\n"
        f"Document name: {document_name}\n"
        f"Framework: {framework_text}\n"
        f"Focus: {focus_text}\n\n"
        "Document excerpt:\n"
        f"{excerpt}"
    )


def summarize_document_text(document_text: str, *, limit: int | None = None) -> str:
    max_chars = max(1, int(limit or get_document_excerpt_chars()))
    text = str(document_text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[truncated]"


def infer_assessment_status(text: str) -> str:
    normalized = str(text or "").lower()
    if not normalized:
        return "unknown"
    if any(
        marker in normalized
        for marker in ("non-compliant", "not compliant", "critical gap", "major gap")
    ):
        return "non_compliant"
    if any(
        marker in normalized
        for marker in (
            "gap",
            "missing",
            "deviation",
            "needs review",
            "needs remediation",
        )
    ):
        return "needs_attention"
    if "compliant" in normalized or "aligned" in normalized:
        return "potentially_compliant"
    return "unknown"
