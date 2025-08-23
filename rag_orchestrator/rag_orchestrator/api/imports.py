# rag_orchestrator/rag_orchestrator/api/imports.py
from __future__ import annotations

import importlib
import importlib.util
import logging
from typing import List, Tuple

log = logging.getLogger("rag_orchestrator.imports")


def is_installed(pkg: str) -> bool:
    """Keep your helper: check if a top-level package is importable."""
    return importlib.util.find_spec(pkg) is not None


def _safe_import(module_path: str) -> Tuple[str, bool, str | None]:
    """
    Import a module for its side-effects (agent registry `register(...)`),
    but never crash the server if one module fails.
    Returns (module_path, ok, error_message).
    """
    try:
        importlib.import_module(module_path)
        log.info("Loaded builtin agent module: %s", module_path)
        return module_path, True, None
    except Exception as e:
        log.exception("Failed to load builtin agent module: %s", module_path)
        return module_path, False, str(e)


def load_builtin_agents() -> List[str]:
    """
    Import all builtin agent modules so they register themselves
    with the global registry via import side-effects.

    Call this once at app startup (see api/app.py).
    """
    modules = [
        "rag_orchestrator.agents.builtin.retriever",
        "rag_orchestrator.agents.builtin.compressor",
        "rag_orchestrator.agents.builtin.reranker",
        "rag_orchestrator.agents.builtin.drafting",
        "rag_orchestrator.agents.builtin.validator",
        "rag_orchestrator.agents.builtin.dialogue",
        "rag_orchestrator.agents.builtin.coordinator",
    ]

    loaded: List[str] = []
    for mod in modules:
        _, ok, _ = _safe_import(mod)
        if ok:
            loaded.append(mod)

    if not loaded:
        log.warning("No builtin agents were loaded. Registry will be empty.")
    else:
        log.info("Builtin agents loaded: %s", ", ".join(loaded))

    return loaded
