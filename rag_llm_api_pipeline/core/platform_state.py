from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_RECENT_ROUTE_LIMIT = 50
_recent_routes: deque[dict[str, Any]] = deque(maxlen=_RECENT_ROUTE_LIMIT)
_lock = Lock()


def record_query_route(event: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        _recent_routes.appendleft(dict(event))
    return event


def list_recent_routes(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        return list(_recent_routes)[: max(0, limit)]
