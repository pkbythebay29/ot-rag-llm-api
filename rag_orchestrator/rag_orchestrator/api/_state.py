import asyncio, os
from rag_orchestrator.runtime.batcher_pool import BatcherPool
from batching.gatekeeper import Gatekeeper, TenantPolicy
from .config_bridge import load_bridge_config, resolve_system_yaml
from ._state_systems import ProviderPool
from runtime.manager import AgentManager

DEFAULT_SYSTEM = os.getenv("SYSTEM_NAME")
SYSTEMS_ROOT = os.getenv("SYSTEMS_ROOT", "config/systems")
FALLBACK_YAML = os.getenv("SYSTEM_YAML", "config/system.yaml")

default_yaml = resolve_system_yaml(DEFAULT_SYSTEM, SYSTEMS_ROOT, FALLBACK_YAML)
_cfg = load_bridge_config(default_yaml)

provider_pool = ProviderPool(SYSTEMS_ROOT, FALLBACK_YAML)
batchers = BatcherPool()


async def _forward_generate(payloads: list[str]) -> list[str]:
    prov = provider_pool.get(DEFAULT_SYSTEM)
    return await prov.forward_batch(payloads)


async def _forward_embed(payloads: list[str]) -> list[str]:
    prov = provider_pool.get(DEFAULT_SYSTEM)
    vecs = await prov.embed(payloads)
    return [str(v) for v in vecs]


async def _forward_rerank(payloads: list[str]) -> list[str]:
    return payloads  # plug cross-encoder here


async def _forward_validate(payloads: list[str]) -> list[str]:
    return await _forward_generate(payloads)


batchers.register(
    "generate",
    _forward_generate,
    max_batch=_cfg.batch.max_batch,
    max_latency_ms=_cfg.batch.max_latency_ms,
)
batchers.register(
    "embed",
    _forward_embed,
    max_batch=_cfg.batch.max_batch,
    max_latency_ms=_cfg.batch.max_latency_ms,
)
batchers.register(
    "rerank",
    _forward_rerank,
    max_batch=_cfg.batch.max_batch,
    max_latency_ms=_cfg.batch.max_latency_ms,
)
batchers.register(
    "validate",
    _forward_validate,
    max_batch=_cfg.batch.max_batch,
    max_latency_ms=_cfg.batch.max_latency_ms,
)

manager = AgentManager()
gate = Gatekeeper(lambda payload, to: batchers.submit("generate", payload, timeout=to))

_started = False


async def ensure_started():
    global _started
    if not _started:
        await batchers.start()
        gate.set_policy(
            "default",
            TenantPolicy(
                rps=_cfg.gate.rps, burst=_cfg.gate.burst, timeout_s=_cfg.gate.timeout_s
            ),
        )
        _started = True


ensure_started_task = asyncio.create_task(ensure_started())
