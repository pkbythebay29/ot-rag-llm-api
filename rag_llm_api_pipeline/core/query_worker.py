from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from multiprocessing import get_context
from typing import Any

from rag_llm_api_pipeline.core.model_selection import (
    resolve_runtime_selection,
    runtime_signature,
    summarize_runtime,
)
from rag_llm_api_pipeline.core.orchestrator import get_orchestrator

_executors: dict[str, ProcessPoolExecutor] = {}
_executor_lock = threading.Lock()
_status_lock = threading.Lock()
_worker_status: dict[str, Any] = {
    "mode": "isolated_process",
    "state": "idle",
    "last_error": None,
    "last_started_at": None,
    "last_finished_at": None,
    "last_worker_pid": None,
    "active_runtime_signature": None,
    "worker_pools": {},
}


def _run_query_in_worker(
    system_name: str, question: str, runtime_selection: dict[str, Any] | None = None
) -> dict[str, Any]:
    result = get_orchestrator().run_query(
        system_name=system_name,
        question=question,
        model_selection=runtime_selection,
    )
    normalized = dict(result or {})
    normalized["worker_pid"] = os.getpid()
    normalized["worker_finished_at"] = time.time()
    normalized["runtime"] = summarize_runtime(runtime_selection or {})
    return normalized


def _pool_snapshot() -> dict[str, Any]:
    with _executor_lock:
        return {signature: {"state": "ready"} for signature in _executors}


def _get_executor(signature: str) -> ProcessPoolExecutor:
    with _executor_lock:
        executor = _executors.get(signature)
        if executor is None:
            executor = ProcessPoolExecutor(
                max_workers=1,
                mp_context=get_context("spawn"),
            )
            _executors[signature] = executor
        return executor


def _drop_executor(signature: str | None = None) -> None:
    global _executors
    with _executor_lock:
        if signature is None:
            executors = list(_executors.values())
            _executors = {}
        else:
            executor = _executors.pop(signature, None)
            executors = [executor] if executor is not None else []
    for executor in executors:
        executor.shutdown(wait=False, cancel_futures=True)


def _set_status(**updates: Any) -> None:
    with _status_lock:
        _worker_status.update(updates)
        _worker_status["worker_pools"] = _pool_snapshot()


def get_query_worker_status() -> dict[str, Any]:
    with _status_lock:
        snapshot = dict(_worker_status)
    snapshot["worker_pools"] = _pool_snapshot()
    return snapshot


def reset_query_worker(reason: str | None = None) -> dict[str, Any]:
    _drop_executor()
    _set_status(
        state="idle",
        last_error=reason,
        last_finished_at=time.time(),
        last_worker_pid=None,
        active_runtime_signature=None,
    )
    return get_query_worker_status()


def run_query_in_worker(
    system_name: str,
    question: str,
    *,
    runtime_selection: dict[str, Any] | None = None,
    timeout_sec: float = 900.0,
) -> dict[str, Any]:
    resolved_runtime = resolve_runtime_selection(overrides=runtime_selection)
    signature = runtime_signature(resolved_runtime)
    _set_status(
        state="running",
        last_error=None,
        last_started_at=time.time(),
        active_runtime_signature=signature,
    )
    try:
        future = _get_executor(signature).submit(
            _run_query_in_worker,
            system_name,
            question,
            resolved_runtime,
        )
        result = future.result(timeout=timeout_sec)
        _set_status(
            state="idle",
            last_finished_at=time.time(),
            last_worker_pid=result.get("worker_pid"),
            active_runtime_signature=signature,
        )
        return result
    except BrokenProcessPool as exc:
        _drop_executor(signature)
        _set_status(
            state="crashed",
            last_error=f"Query worker crashed: {exc}",
            last_finished_at=time.time(),
            active_runtime_signature=signature,
        )
        raise RuntimeError(
            "The isolated query worker crashed during model initialization or generation."
        ) from exc
    except Exception as exc:
        _set_status(
            state="failed",
            last_error=str(exc),
            last_finished_at=time.time(),
            active_runtime_signature=signature,
        )
        raise
