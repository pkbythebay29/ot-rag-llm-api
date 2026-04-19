from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config

DEFAULT_INFERENCE_CATALOG: dict[str, dict[str, Any]] = {
    "qwen-0.5b-instruct": {
        "label": "Qwen 2.5 0.5B Instruct",
        "huggingface_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "size": "small",
        "recommended_for_low_resource": True,
        "description": "Smallest local instruct model for constrained CPU or low-memory hosts.",
    },
    "qwen-1.5b-instruct": {
        "label": "Qwen 2.5 1.5B Instruct",
        "huggingface_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "size": "medium",
        "recommended_for_low_resource": True,
        "description": "Balanced local instruct model when quality matters but memory is still limited.",
    },
    "qwen-3b-instruct": {
        "label": "Qwen 2.5 3B Instruct",
        "huggingface_id": "Qwen/Qwen2.5-3B-Instruct",
        "size": "large",
        "recommended_for_low_resource": False,
        "description": "Higher-quality local instruct model that benefits from stronger hardware.",
    },
}

DEFAULT_EMBEDDING_CATALOG: dict[str, dict[str, Any]] = {
    "minilm-l6": {
        "label": "all-MiniLM-L6-v2",
        "huggingface_id": "sentence-transformers/all-MiniLM-L6-v2",
        "size": "small",
        "recommended_for_low_resource": True,
        "description": "Compact embedding model with the best memory footprint for shared use.",
    },
    "bge-small-en-v1.5": {
        "label": "BAAI/bge-small-en-v1.5",
        "huggingface_id": "BAAI/bge-small-en-v1.5",
        "size": "small",
        "recommended_for_low_resource": True,
        "description": "Stronger compact embedding model for quality-sensitive search workloads.",
    },
    "bge-base-en-v1.5": {
        "label": "BAAI/bge-base-en-v1.5",
        "huggingface_id": "BAAI/bge-base-en-v1.5",
        "size": "medium",
        "recommended_for_low_resource": False,
        "description": "Higher-capacity embedding model when memory pressure is acceptable.",
    },
}

DEFAULT_RUNTIME_PROFILES: dict[str, dict[str, Any]] = {
    "shared-compact": {
        "label": "Shared Compact",
        "description": "Reuse the same compact inference and embedding models across agents.",
        "model_profile": "cpu-compact",
        "inference_model": "qwen-0.5b-instruct",
        "embedding_model": "minilm-l6",
        "recommend_for_low_resource": True,
        "reuse_recommended": True,
    },
    "balanced-search": {
        "label": "Balanced Search",
        "description": "Balanced inference with a stronger search encoder for most local deployments.",
        "model_profile": "cpu-balanced",
        "inference_model": "qwen-1.5b-instruct",
        "embedding_model": "bge-small-en-v1.5",
        "recommend_for_low_resource": True,
        "reuse_recommended": False,
    },
    "quality-gpu": {
        "label": "Quality GPU",
        "description": "Higher-quality inference and retrieval intended for stronger GPU hosts.",
        "model_profile": "gpu-quality",
        "inference_model": "qwen-3b-instruct",
        "embedding_model": "bge-base-en-v1.5",
        "recommend_for_low_resource": False,
        "reuse_recommended": False,
    },
}

DEFAULT_AGENT_ASSIGNMENTS: dict[str, Any] = {
    "default": {
        "runtime_profile": "shared-compact",
    },
    "by_agent_type": {
        "retriever": {
            "runtime_profile": "shared-compact",
        },
        "dialogue": {
            "runtime_profile": "balanced-search",
        },
        "regulatory": {
            "runtime_profile": "balanced-search",
        },
    },
    "by_system": {},
    "by_agent_name": {},
}

DEFAULT_RESOURCE_POLICY: dict[str, Any] = {
    "low_memory_threshold_gb": 4.0,
    "high_cpu_threshold_percent": 90.0,
    "recommended_shared_profile": "shared-compact",
    "smaller_runtime_profiles": ["shared-compact", "balanced-search"],
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _copy_mapping(value: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(value or {})


def _models_section(config: dict[str, Any]) -> dict[str, Any]:
    models = config.get("models", {})
    return models if isinstance(models, dict) else {}


def slugify_model_ref(value: str) -> str:
    normalized = _SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-")
    return normalized or "custom"


def get_inference_catalog(
    config: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    resolved = config or load_config() or {}
    configured = _models_section(resolved).get("inference_catalog")
    catalog = _copy_mapping(DEFAULT_INFERENCE_CATALOG)
    if isinstance(configured, dict):
        for key, payload in configured.items():
            if isinstance(key, str) and isinstance(payload, dict):
                merged = dict(catalog.get(key, {}))
                merged.update(payload)
                catalog[key] = merged
    return catalog


def get_embedding_catalog(
    config: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    resolved = config or load_config() or {}
    configured = _models_section(resolved).get("embedding_catalog")
    catalog = _copy_mapping(DEFAULT_EMBEDDING_CATALOG)
    if isinstance(configured, dict):
        for key, payload in configured.items():
            if isinstance(key, str) and isinstance(payload, dict):
                merged = dict(catalog.get(key, {}))
                merged.update(payload)
                catalog[key] = merged
    return catalog


def get_runtime_profiles(
    config: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    resolved = config or load_config() or {}
    configured = _models_section(resolved).get("runtime_profiles")
    profiles = _copy_mapping(DEFAULT_RUNTIME_PROFILES)
    if isinstance(configured, dict):
        for key, payload in configured.items():
            if isinstance(key, str) and isinstance(payload, dict):
                merged = dict(profiles.get(key, {}))
                merged.update(payload)
                profiles[key] = merged
    return profiles


def get_agent_assignments(config: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = config or load_config() or {}
    configured = _models_section(resolved).get("agent_assignments")
    assignments = _copy_mapping(DEFAULT_AGENT_ASSIGNMENTS)
    if isinstance(configured, dict):
        for key in ("default", "by_agent_type", "by_system", "by_agent_name"):
            payload = configured.get(key)
            if isinstance(payload, dict):
                merged = dict(assignments.get(key, {}))
                merged.update(payload)
                assignments[key] = merged
    return assignments


def get_resource_policy(config: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = config or load_config() or {}
    configured = _models_section(resolved).get("resource_policy")
    policy = dict(DEFAULT_RESOURCE_POLICY)
    if isinstance(configured, dict):
        policy.update(configured)
    return policy


def _resolve_catalog_entry(
    catalog: dict[str, dict[str, Any]],
    requested: str | None,
) -> tuple[str, dict[str, Any]]:
    requested_value = str(requested or "").strip()
    if not requested_value:
        raise ValueError("A model reference is required.")

    if requested_value in catalog:
        payload = dict(catalog[requested_value])
        payload.setdefault("huggingface_id", requested_value)
        payload["key"] = requested_value
        payload.setdefault("label", payload["huggingface_id"])
        return requested_value, payload

    for key, payload in catalog.items():
        if str(payload.get("huggingface_id")) == requested_value:
            resolved = dict(payload)
            resolved["key"] = key
            resolved.setdefault("label", resolved.get("huggingface_id", key))
            return key, resolved

    custom_key = slugify_model_ref(requested_value)
    return custom_key, {
        "key": custom_key,
        "label": requested_value,
        "huggingface_id": requested_value,
        "size": "custom",
        "recommended_for_low_resource": False,
        "description": "Custom Hugging Face model provided outside the configured catalog.",
    }


def resolve_inference_model(
    config: dict[str, Any] | None = None,
    requested: str | None = None,
) -> dict[str, Any]:
    resolved = config or load_config() or {}
    models = _models_section(resolved)
    requested_value = requested or str(models.get("llm_model") or "").strip()
    key, payload = _resolve_catalog_entry(
        get_inference_catalog(resolved), requested_value
    )
    payload["key"] = key
    return payload


def resolve_embedding_model(
    config: dict[str, Any] | None = None,
    requested: str | None = None,
) -> dict[str, Any]:
    resolved = config or load_config() or {}
    retriever = resolved.get("retriever", {}) or {}
    requested_value = requested or str(retriever.get("embedding_model") or "").strip()
    key, payload = _resolve_catalog_entry(
        get_embedding_catalog(resolved), requested_value
    )
    payload["key"] = key
    return payload


def _profile_overrides(
    profiles: dict[str, dict[str, Any]], profile_name: str | None
) -> dict[str, Any]:
    if not profile_name:
        return {}
    payload = profiles.get(profile_name)
    if not isinstance(payload, dict):
        raise ValueError(f"Unknown runtime profile: {profile_name}")
    return dict(payload)


def _assignment_overrides(
    assignments: dict[str, Any],
    *,
    agent_type: str | None,
    agent_name: str | None,
    system_name: str | None,
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    default_payload = assignments.get("default")
    if isinstance(default_payload, dict):
        selected.update(default_payload)

    by_agent_type = assignments.get("by_agent_type")
    if agent_type and isinstance(by_agent_type, dict):
        payload = by_agent_type.get(agent_type)
        if isinstance(payload, dict):
            selected.update(payload)

    by_system = assignments.get("by_system")
    if system_name and isinstance(by_system, dict):
        payload = by_system.get(system_name)
        if isinstance(payload, dict):
            selected.update(payload)

    by_agent_name = assignments.get("by_agent_name")
    if agent_name and isinstance(by_agent_name, dict):
        payload = by_agent_name.get(agent_name)
        if isinstance(payload, dict):
            selected.update(payload)

    return selected


def resolve_runtime_selection(
    config: dict[str, Any] | None = None,
    *,
    runtime_profile: str | None = None,
    inference_model: str | None = None,
    embedding_model: str | None = None,
    agent_type: str | None = None,
    agent_name: str | None = None,
    system_name: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = config or load_config() or {}
    models = _models_section(resolved)
    settings = resolved.get("settings", {}) or {}
    retriever = resolved.get("retriever", {}) or {}
    runtime_profiles = get_runtime_profiles(resolved)
    assignments = get_agent_assignments(resolved)

    runtime: dict[str, Any] = {
        "runtime_profile": None,
        "model_profile": str(models.get("active_profile") or "custom"),
        "llm_model": models.get("llm_model"),
        "embedding_model": retriever.get("embedding_model"),
        "device": models.get("device"),
        "model_precision": models.get("model_precision"),
        "quantization_backend": models.get("quantization_backend"),
        "low_cpu_mem_usage": bool(models.get("low_cpu_mem_usage", True)),
        "use_cpu": bool(settings.get("use_cpu", False)),
        "reuse_recommended": False,
        "recommend_for_low_resource": False,
    }

    assignment_payload = _assignment_overrides(
        assignments,
        agent_type=agent_type,
        agent_name=agent_name,
        system_name=system_name,
    )
    requested_profile = runtime_profile or assignment_payload.get("runtime_profile")
    if requested_profile:
        runtime.update(_profile_overrides(runtime_profiles, str(requested_profile)))
        runtime["runtime_profile"] = str(requested_profile)

    for key, value in assignment_payload.items():
        if key != "runtime_profile":
            runtime[key] = value

    explicit_overrides = dict(overrides or {})
    if inference_model:
        runtime["inference_model"] = inference_model
    if embedding_model:
        runtime["embedding_model"] = embedding_model

    for key, value in explicit_overrides.items():
        if value is not None:
            runtime[key] = value

    if runtime.get("model_profile") and runtime["model_profile"] in (
        models.get("profiles") or {}
    ):
        selected_model_profile = (models.get("profiles") or {}).get(
            runtime["model_profile"], {}
        )
        if isinstance(selected_model_profile, dict):
            for key in (
                "llm_model",
                "device",
                "model_precision",
                "quantization_backend",
                "low_cpu_mem_usage",
                "use_cpu",
            ):
                if key in selected_model_profile:
                    runtime[key] = selected_model_profile[key]

    if inference_model:
        runtime["inference_model"] = inference_model
    if embedding_model:
        runtime["embedding_model"] = embedding_model
    for key, value in explicit_overrides.items():
        if value is not None:
            runtime[key] = value

    resolved_inference = resolve_inference_model(
        resolved,
        requested=str(runtime.get("inference_model") or runtime.get("llm_model") or ""),
    )
    resolved_embedding = resolve_embedding_model(
        resolved,
        requested=str(runtime.get("embedding_model") or ""),
    )

    runtime["inference_model"] = resolved_inference["huggingface_id"]
    runtime["inference_model_key"] = resolved_inference["key"]
    runtime["inference_model_label"] = resolved_inference.get("label")
    runtime["embedding_model"] = resolved_embedding["huggingface_id"]
    runtime["embedding_model_key"] = resolved_embedding["key"]
    runtime["embedding_model_label"] = resolved_embedding.get("label")

    if not runtime.get("llm_model"):
        runtime["llm_model"] = runtime["inference_model"]
    else:
        runtime["llm_model"] = runtime["inference_model"]

    runtime["recommend_for_low_resource"] = bool(
        runtime.get("recommend_for_low_resource")
        or resolved_inference.get("recommended_for_low_resource")
        or resolved_embedding.get("recommended_for_low_resource")
    )
    runtime["reuse_recommended"] = bool(runtime.get("reuse_recommended", False))
    runtime["signature"] = runtime_signature(runtime)
    return runtime


def runtime_signature(runtime: dict[str, Any] | None) -> str:
    payload = runtime or {}
    inference_key = str(
        payload.get("inference_model_key")
        or payload.get("llm_model")
        or "default-inference"
    )
    embedding_key = str(
        payload.get("embedding_model_key")
        or payload.get("embedding_model")
        or "default-embedding"
    )
    device = str(payload.get("device") or "auto")
    precision = str(payload.get("model_precision") or "auto")
    quant = str(payload.get("quantization_backend") or "auto")
    use_cpu = "cpu" if payload.get("use_cpu") else "mixed"
    return "|".join([inference_key, embedding_key, device, precision, quant, use_cpu])


def embedding_index_slug(runtime: dict[str, Any] | None) -> str:
    payload = runtime or {}
    model_ref = str(
        payload.get("embedding_model_key")
        or payload.get("embedding_model")
        or "default"
    )
    return slugify_model_ref(model_ref)


def summarize_runtime(runtime: dict[str, Any] | None) -> dict[str, Any]:
    payload = runtime or {}
    return {
        "runtime_profile": payload.get("runtime_profile"),
        "model_profile": payload.get("model_profile"),
        "inference_model": payload.get("inference_model"),
        "embedding_model": payload.get("embedding_model"),
        "device": payload.get("device"),
        "quantization_backend": payload.get("quantization_backend"),
        "use_cpu": bool(payload.get("use_cpu", False)),
        "recommend_for_low_resource": bool(
            payload.get("recommend_for_low_resource", False)
        ),
        "reuse_recommended": bool(payload.get("reuse_recommended", False)),
        "signature": payload.get("signature"),
    }
