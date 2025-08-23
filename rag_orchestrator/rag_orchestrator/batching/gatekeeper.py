from __future__ import annotations
import asyncio, time
from dataclasses import dataclass
from typing import Any, Optional, Dict  # ### NEW


class QueueFull429(Exception): ...


class RateLimited429(Exception): ...


@dataclass
class TenantPolicy:
    rps: float = 20.0
    burst: int = 40
    timeout_s: float = 30.0


class _Bucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.capacity = burst
        self.tokens = burst
        self.ts = time.perf_counter()
        self.lock = asyncio.Lock()

    async def allow(self) -> bool:
        async with self.lock:
            now = time.perf_counter()
            self.tokens = min(self.capacity, self.tokens + (now - self.ts) * self.rate)
            self.ts = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


class Gatekeeper:
    def __init__(self, submit_fn):
        self._submit = submit_fn
        self._policies: dict[str, TenantPolicy] = {}
        self._buckets: dict[str, _Bucket] = {}

    def set_policy(self, tenant: str, policy: TenantPolicy) -> None:
        self._policies[tenant] = policy
        self._buckets[tenant] = _Bucket(policy.rps, policy.burst)

    async def handle(
        self,
        tenant: str,
        payload: Any,
        *,
        meta: Optional[Dict[str, Any]] = None,  # ### NEW (optional)
    ):
        policy = self._policies.get(tenant, TenantPolicy())
        buck = self._buckets.setdefault(tenant, _Bucket(policy.rps, policy.burst))
        if not await buck.allow():
            raise RateLimited429("rate limited")
        try:
            # pass timeout as named kwarg; include tenant meta for telemetry
            meta = {"tenant": tenant, **(meta or {})}  # ### NEW
            return await self._submit(
                payload, timeout=policy.timeout_s, meta=meta
            )  # ### NEW
        except asyncio.QueueFull:
            raise QueueFull429("queue full")
