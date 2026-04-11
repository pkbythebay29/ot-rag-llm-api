from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from multiprocessing import get_context
from typing import Any

from rag_llm_api_pipeline.core.orchestrator import get_orchestrator

_executor: ProcessPoolExecutor | None = None
_executor_lock = threading.Lock()
_status_lock = threading.Lock()
_worker_status: dict[str, Any] = {
    "mode": "isolated_process",
    "state": "idle",
    "last_error": None,
    "last_started_at": None,
    "last_finished_at": None,
    "last_worker_pid": None,
}


def _run_query_in_worker(system_name: str, question: str) -> dict[str, Any]:
    result = get_orchestrator().run_query(system_name=system_name, question=question)
    normalized = dict(result or {})
    normalized["worker_pid"] = os.getpid()
    normalized["worker_finished_at"] = time.time()
    return normalized


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ProcessPoolExecutor(
                max_workers=1,
                mp_context=get_context("spawn"),
            )
        return _executor


def _reset_executor() -> None:
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False, cancel_futures=True)
            _executor = None


def _set_status(**updates: Any) -> None:
    with _status_lock:
        _worker_status.update(updates)


def get_query_worker_status() -> dict[str, Any]:
    with _status_lock:
        return dict(_worker_status)


def reset_query_worker(reason: str | None = None) -> dict[str, Any]:
    _reset_executor()
    _set_status(
        state="idle",
        last_error=reason,
        last_finished_at=time.time(),
        last_worker_pid=None,
    )
    return get_query_worker_status()


def run_query_in_worker(
    system_name: str, question: str, *, timeout_sec: float = 900.0
) -> dict[str, Any]:
    _set_status(
        state="running",
        last_error=None,
        last_started_at=time.time(),
    )
    try:
        future = _get_executor().submit(_run_query_in_worker, system_name, question)
        result = future.result(timeout=timeout_sec)
        _set_status(
            state="idle",
            last_finished_at=time.time(),
            last_worker_pid=result.get("worker_pid"),
        )
        return result
    except BrokenProcessPool as exc:
        _reset_executor()
        _set_status(
            state="crashed",
            last_error=f"Query worker crashed: {exc}",
            last_finished_at=time.time(),
        )
        raise RuntimeError(
            "The isolated query worker crashed during model initialization or generation."
        ) from exc
    except Exception as exc:
        _set_status(
            state="failed",
            last_error=str(exc),
            last_finished_at=time.time(),
        )
        raise
