from __future__ import annotations

import os

from fastapi import Header, HTTPException, status

from rag_llm_api_pipeline.config_loader import load_config

DEFAULT_API_KEY_ENV = "KRIONIS_REVIEW_API_KEY"


def _security_config() -> dict:
    config = load_config() or {}
    return config.get("security", {})


def get_configured_api_key() -> str | None:
    security_cfg = _security_config()
    env_var = str(security_cfg.get("api_key_env_var", DEFAULT_API_KEY_ENV))
    return os.getenv(env_var) or security_cfg.get("api_key")


def get_user_id(header_value: str | None, default: str = "anonymous") -> str:
    return (header_value or default).strip() or default


def validate_api_key_header(x_api_key: str | None = Header(default=None)) -> str:
    configured_key = get_configured_api_key()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review API key is not configured.",
        )
    if x_api_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return configured_key
