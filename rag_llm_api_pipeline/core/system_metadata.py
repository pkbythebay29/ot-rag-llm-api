from __future__ import annotations

from typing import Any

from rag_llm_api_pipeline import __version__
from rag_llm_api_pipeline.config_loader import load_config


def get_system_metadata() -> dict[str, Any]:
    config = load_config() or {}
    metadata = config.get("system_metadata", {})
    llm_cfg = config.get("llm", {})
    model_cfg = config.get("models", {})

    return {
        "system_name": metadata.get("system_name", "Krionis HITL RAG API"),
        "version": metadata.get("version", __version__),
        "component_type": metadata.get("component_type", "GAMP Category 5"),
        "agent_system_id": metadata.get("agent_system_id", "krionis-rag-api"),
        "module_classification": metadata.get(
            "module_classification",
            {
                "configuration": ["config/system.yaml"],
                "custom_modules": [
                    "rag_llm_api_pipeline/core",
                    "rag_llm_api_pipeline/db",
                    "rag_llm_api_pipeline/api",
                    "rag_llm_api_pipeline/ui",
                ],
            },
        ),
        "model_version": model_cfg.get("llm_model", "model-version-placeholder"),
        "prompt_version": llm_cfg.get("prompt_version", "prompt-version-placeholder"),
    }
