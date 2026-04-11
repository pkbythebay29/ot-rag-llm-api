from __future__ import annotations

from typing import Any

from rag_llm_api_pipeline.config_loader import (
    load_config,
    load_raw_config,
    save_config,
)
from rag_llm_api_pipeline.core.query_worker import reset_query_worker

DEFAULT_MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "cpu-compact": {
        "label": "CPU Compact",
        "description": "Smallest local profile for reliable CPU and air-gapped bring-up.",
        "llm_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "device": "cpu",
        "use_cpu": True,
        "model_precision": "auto",
        "quantization_backend": "dynamic-int8",
        "low_cpu_mem_usage": True,
    },
    "cpu-balanced": {
        "label": "CPU Balanced",
        "description": "A stronger CPU profile that still prefers int8 quantization.",
        "llm_model": "Qwen/Qwen2.5-1.5B-Instruct",
        "device": "cpu",
        "use_cpu": True,
        "model_precision": "auto",
        "quantization_backend": "dynamic-int8",
        "low_cpu_mem_usage": True,
    },
    "gpu-quality": {
        "label": "GPU Quality",
        "description": "Higher-quality GPU profile with non-quantized runtime on CUDA.",
        "llm_model": "Qwen/Qwen2.5-3B-Instruct",
        "device": "auto",
        "use_cpu": False,
        "model_precision": "auto",
        "quantization_backend": "auto",
        "low_cpu_mem_usage": True,
    },
}

PROFILE_FIELD_KEYS = (
    "llm_model",
    "device",
    "model_precision",
    "quantization_backend",
    "low_cpu_mem_usage",
)


def _models_section(cfg: dict[str, Any]) -> dict[str, Any]:
    models = cfg.setdefault("models", {})
    if not isinstance(models, dict):
        models = {}
        cfg["models"] = models
    return models


def _settings_section(cfg: dict[str, Any]) -> dict[str, Any]:
    settings = cfg.setdefault("settings", {})
    if not isinstance(settings, dict):
        settings = {}
        cfg["settings"] = settings
    return settings


def _get_profiles(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    models = cfg.get("models", {}) or {}
    configured = models.get("profiles")
    if not isinstance(configured, dict) or not configured:
        return dict(DEFAULT_MODEL_PROFILES)

    profiles: dict[str, dict[str, Any]] = {}
    for name, payload in configured.items():
        if isinstance(name, str) and isinstance(payload, dict):
            merged = dict(DEFAULT_MODEL_PROFILES.get(name, {}))
            merged.update(payload)
            profiles[name] = merged
    for name, payload in DEFAULT_MODEL_PROFILES.items():
        profiles.setdefault(name, dict(payload))
    return profiles


def get_model_profiles(config: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = config or load_config()
    raw_cfg = load_raw_config()
    models = resolved.get("models", {}) or {}
    settings = resolved.get("settings", {}) or {}
    profiles = _get_profiles(raw_cfg)
    active_profile = str(models.get("active_profile") or "custom").strip() or "custom"

    items: list[dict[str, Any]] = []
    current_signature = {
        "llm_model": models.get("llm_model"),
        "device": models.get("device"),
        "model_precision": models.get("model_precision"),
        "quantization_backend": models.get("quantization_backend"),
        "low_cpu_mem_usage": bool(models.get("low_cpu_mem_usage", True)),
        "use_cpu": bool(settings.get("use_cpu", False)),
    }
    for name, payload in profiles.items():
        signature = {
            "llm_model": payload.get("llm_model"),
            "device": payload.get("device"),
            "model_precision": payload.get("model_precision"),
            "quantization_backend": payload.get("quantization_backend"),
            "low_cpu_mem_usage": bool(payload.get("low_cpu_mem_usage", True)),
            "use_cpu": bool(payload.get("use_cpu", False)),
        }
        items.append(
            {
                "name": name,
                "label": payload.get("label", name),
                "description": payload.get("description", ""),
                "config": signature,
                "is_active": active_profile == name,
                "matches_current_runtime": signature == current_signature,
            }
        )

    return {
        "active_profile": active_profile,
        "current": current_signature,
        "profiles": items,
    }


def apply_model_profile(
    *,
    profile_name: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_cfg = load_raw_config()
    resolved_cfg = load_config()
    models = _models_section(raw_cfg)
    settings = _settings_section(raw_cfg)
    profiles = _get_profiles(raw_cfg)
    overrides = dict(overrides or {})

    selected_profile = None
    if profile_name:
        selected_profile = profiles.get(profile_name)
        if selected_profile is None:
            raise ValueError(f"Unknown model profile: {profile_name}")

    if selected_profile is not None:
        for key in PROFILE_FIELD_KEYS:
            value = selected_profile.get(key)
            if value is not None:
                models[key] = value
        settings["use_cpu"] = bool(
            selected_profile.get("use_cpu", settings.get("use_cpu", False))
        )
        models["active_profile"] = profile_name

    for key in PROFILE_FIELD_KEYS:
        if key in overrides and overrides[key] is not None:
            models[key] = overrides[key]
    if "use_cpu" in overrides and overrides["use_cpu"] is not None:
        settings["use_cpu"] = bool(overrides["use_cpu"])
    if overrides:
        models["active_profile"] = profile_name or "custom"

    if "profiles" not in models or not isinstance(models.get("profiles"), dict):
        models["profiles"] = profiles

    config_path = save_config(raw_cfg)
    reset_query_worker(
        "Model configuration changed. The next query will load the selected profile."
    )

    refreshed = load_config()
    summary = get_model_profiles(refreshed)
    summary["config_path"] = config_path
    summary["worker_reset"] = True
    summary["message"] = (
        "Model profile saved. The next query will use the updated model configuration."
    )
    summary["previous_llm_model"] = resolved_cfg.get("models", {}).get("llm_model")
    summary["current_llm_model"] = refreshed.get("models", {}).get("llm_model")
    return summary
