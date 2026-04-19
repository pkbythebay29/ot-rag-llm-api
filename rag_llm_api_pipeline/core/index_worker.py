from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from threading import Lock
from typing import Any


def _run_index_build(
    system_name: str, model_selection: dict[str, Any] | None = None
) -> dict[str, Any]:
    from rag_llm_api_pipeline.retriever import build_index

    return build_index(system_name, model_selection=model_selection)


_executor: ProcessPoolExecutor | None = None
_lock = Lock()
_status: dict[str, Any] = {
    "mode": "isolated_process",
    "state": "idle",
    "last_error": None,
    "last_started_at": None,
    "last_finished_at": None,
}


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ProcessPoolExecutor(
                max_workers=1, mp_context=get_context("spawn")
            )
        return _executor


def rebuild_index_in_worker(
    system_name: str,
    model_selection: dict[str, Any] | None = None,
    timeout_sec: float = 900.0,
) -> dict[str, Any]:
    global _executor
    _status["state"] = "running"
    _status["last_error"] = None
    _status["last_started_at"] = time.time()

    try:
        future = _get_executor().submit(_run_index_build, system_name, model_selection)
        result = future.result(timeout=timeout_sec)
        _status["state"] = "idle"
        _status["last_finished_at"] = time.time()
        return result
    except Exception as exc:
        with _lock:
            if _executor is not None:
                _executor.shutdown(wait=False, cancel_futures=True)
                _executor = None
        _status["state"] = "crashed"
        _status["last_error"] = str(exc)
        _status["last_finished_at"] = time.time()
        raise RuntimeError(
            f"Index rebuild worker failed for '{system_name}': {exc}"
        ) from exc


def get_index_worker_status() -> dict[str, Any]:
    return dict(_status)
