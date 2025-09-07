from __future__ import annotations
from typing import Callable, Dict, Any, Awaitable
from rag_orchestrator.batching.microbatch import AsyncMicroBatcher

TaskKey = str


class BatcherPool:
    def __init__(self) -> None:
        self._pool: Dict[TaskKey, AsyncMicroBatcher] = {}
        self._started = False

    def register(
        self,
        key: TaskKey,
        forward_fn: Callable[[list[Any]], Awaitable[list[Any]]],
        *,
        max_batch: int = 8,
        max_latency_ms: int = 5,
        max_queue: int = 1024,
    ) -> None:
        if key in self._pool:
            return
        self._pool[key] = AsyncMicroBatcher(
            forward_fn,
            max_batch=max_batch,
            max_latency_ms=max_latency_ms,
            max_queue=max_queue,
        )

    async def start(self) -> None:
        if self._started:
            return
        for b in self._pool.values():
            await b.start()
        self._started = True

    async def close(self) -> None:
        for b in self._pool.values():
            await b.close()
        self._started = False

    async def submit(
        self, key: TaskKey, payload: Any, *, timeout: float | None = None
    ) -> Any:
        return await self._pool[key].submit(payload, timeout=timeout)
