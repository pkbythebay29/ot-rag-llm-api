from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import yaml

CONFIG_ENV_VAR = "KRIONIS_CONFIG_PATH"
HOME_ENV_VAR = "KRIONIS_HOME"
DEFAULT_HOME_DIRNAME = ".krionis"
PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULTS_DIR = PACKAGE_ROOT / "defaults"
DEFAULT_CONFIG_PATH = DEFAULTS_DIR / "system.yaml"
DEFAULT_SAMPLE_MANUAL_PATH = DEFAULTS_DIR / "sample.txt"


def _runtime_home_candidates() -> list[Path]:
    override = os.getenv(HOME_ENV_VAR)
    if override:
        return [Path(override).expanduser().resolve()]

    candidates: list[Path] = []
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        candidates.append((Path(local_app_data) / "Krionis").resolve())
    candidates.append((Path.home() / DEFAULT_HOME_DIRNAME).resolve())
    candidates.append((Path.cwd() / DEFAULT_HOME_DIRNAME).resolve())

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        marker = str(candidate).lower()
        if marker not in seen:
            seen.add(marker)
            unique_candidates.append(candidate)
    return unique_candidates


def get_runtime_home() -> Path:
    return _runtime_home_candidates()[0]


def ensure_runtime_home() -> Path:
    last_error: OSError | None = None

    for runtime_home in _runtime_home_candidates():
        try:
            (runtime_home / "config").mkdir(parents=True, exist_ok=True)
            (runtime_home / "data" / "manuals").mkdir(parents=True, exist_ok=True)
            (runtime_home / "data" / "reviews").mkdir(parents=True, exist_ok=True)
            (runtime_home / "data" / "audit").mkdir(parents=True, exist_ok=True)
            (runtime_home / "data" / "feedback").mkdir(parents=True, exist_ok=True)
            (runtime_home / "indices").mkdir(parents=True, exist_ok=True)

            target_config = runtime_home / "config" / "system.yaml"
            if DEFAULT_CONFIG_PATH.exists() and not target_config.exists():
                shutil.copyfile(DEFAULT_CONFIG_PATH, target_config)

            target_sample = runtime_home / "data" / "manuals" / "sample.txt"
            if DEFAULT_SAMPLE_MANUAL_PATH.exists() and not target_sample.exists():
                shutil.copyfile(DEFAULT_SAMPLE_MANUAL_PATH, target_sample)

            return runtime_home
        except OSError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("No runtime home candidates available for Krionis.")


def get_config_path() -> str:
    explicit = os.getenv(CONFIG_ENV_VAR)
    if explicit:
        return str(Path(explicit).expanduser().resolve())

    repo_local = (Path.cwd() / "config" / "system.yaml").resolve()
    if repo_local.exists():
        return str(repo_local)

    runtime_home = ensure_runtime_home()
    return str((runtime_home / "config" / "system.yaml").resolve())


def get_config_root(config_path: str | Path | None = None) -> Path:
    cfg_path = Path(config_path or get_config_path()).expanduser().resolve()
    if cfg_path.parent.name == "config":
        return cfg_path.parent.parent
    return cfg_path.parent


def resolve_runtime_path(
    value: str | None, *, config_path: str | Path | None = None
) -> str | None:
    if not value:
        return value
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return str(candidate)
    return str((get_config_root(config_path) / candidate).resolve())


def _normalize_runtime_paths(cfg: dict[str, Any], config_path: str) -> dict[str, Any]:
    def _resolve(section: str, key: str) -> None:
        section_data = cfg.get(section)
        if isinstance(section_data, dict) and section_data.get(key):
            section_data[key] = resolve_runtime_path(
                str(section_data[key]), config_path=config_path
            )

    _resolve("settings", "data_dir")
    _resolve("settings", "index_dir")
    _resolve("retriever", "index_dir")
    _resolve("review_store", "sqlite_path")
    _resolve("audit", "log_path")
    _resolve("feedback", "corrections_path")
    _resolve("feedback", "quality_path")
    _resolve("feedback", "metadata_sqlite_path")

    assets = cfg.get("assets")
    if isinstance(assets, list):
        for asset in assets:
            if isinstance(asset, dict) and asset.get("docs_dir"):
                asset["docs_dir"] = resolve_runtime_path(
                    str(asset["docs_dir"]), config_path=config_path
                )

    return cfg


def load_config() -> dict[str, Any]:
    config_path = get_config_path()
    with open(config_path, "r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    return _normalize_runtime_paths(cfg, config_path)
