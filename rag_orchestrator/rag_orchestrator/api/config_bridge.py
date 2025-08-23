from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from pathlib import Path
import yaml


@dataclass
class OrchestratorBatchCfg:
    max_batch: int = 8
    max_latency_ms: int = 5
    max_queue: int = 1024


@dataclass
class OrchestratorGateCfg:
    rps: float = 20.0
    burst: int = 40
    timeout_s: float = 30.0


@dataclass
class BridgeConfig:
    llm: dict[str, Any]
    retriever: dict[str, Any]
    batch: OrchestratorBatchCfg
    gate: OrchestratorGateCfg


def resolve_system_yaml(
    system: str | None, systems_root: str, fallback_yaml: str
) -> str:
    if system:
        cand = Path(systems_root) / system / "system.yaml"
        if cand.exists():
            return str(cand)
    fb = Path(fallback_yaml)
    if fb.exists():
        return str(fb)
    return str(Path("config") / "system.yaml")


def load_bridge_config(path: str) -> BridgeConfig:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    llm = cfg.get("llm", {})
    retr = cfg.get("retriever", {})
    orch = cfg.get("orchestrator", {}) or {}
    b = orch.get("batcher") or {}
    g = (orch.get("gatekeeper") or {}).get("default_tenant") or {}
    return BridgeConfig(
        llm=llm,
        retriever=retr,
        batch=OrchestratorBatchCfg(
            max_batch=b.get("max_batch", 8),
            max_latency_ms=b.get("max_latency_ms", 5),
            max_queue=b.get("max_queue", 1024),
        ),
        gate=OrchestratorGateCfg(
            rps=float(g.get("rps", 20.0)),
            burst=int(g.get("burst", 40)),
            timeout_s=float(g.get("timeout_s", 30.0)),
        ),
    )
