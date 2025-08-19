from __future__ import annotations
import asyncio, time
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class _Req:
    payload: Any
    fut: asyncio.Future

class AsyncMicroBatcher:
    def __init__(self, forward_fn: Callable[[list[Any]], "Any"],
                 *, max_queue: int = 1024, max_batch: int = 8, max_latency_ms: int = 5) -> None:
        self._q: asyncio.Queue[_Req] = asyncio.Queue(maxsize=max_queue)
        self._forward = forward_fn
        self._max_batch = max_batch
        self._window = max_latency_ms / 1000.0
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def close(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def submit(self, payload: Any, *, timeout: float | None = None) -> Any:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._q.put_nowait(_Req(payload, fut))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                first = await asyncio.wait_for(self._q.get(), timeout=0.01)
            except asyncio.TimeoutError:
                continue
            batch = [first]
            deadline = time.perf_counter() + self._window
            while len(batch) < self._max_batch:
                remaining = deadline - time.perf_counter()
                if remaining <= 0: break
                try:
                    nxt = await asyncio.wait_for(self._q.get(), timeout=remaining)
                    batch.append(nxt)
                except asyncio.TimeoutError:
                    break
            try:
                outs = self._forward([r.payload for r in batch])
                if asyncio.iscoroutine(outs): outs = await outs
                assert len(outs) == len(batch), "forward returned mismatched outputs"
            except Exception as e:
                for r in batch:
                    if not r.fut.done(): r.fut.set_exception(e)
            else:
                for r, out in zip(batch, outs):
                    if not r.fut.done(): r.fut.set_result(out)