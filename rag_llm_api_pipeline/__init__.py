"""Top-level package exports kept lazy for compatibility."""

from __future__ import annotations

__version__ = "0.9.0"


def get_answer(*args, **kwargs):
    from .retriever import get_answer as _get_answer

    return _get_answer(*args, **kwargs)


def build_index(*args, **kwargs):
    from .retriever import build_index as _build_index

    return _build_index(*args, **kwargs)


__all__ = ["__version__", "get_answer", "build_index"]
