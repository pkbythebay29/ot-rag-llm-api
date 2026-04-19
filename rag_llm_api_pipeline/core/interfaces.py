from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RetrievalResult:
    question: str
    chunks: list[str]
    context: str
    chunks_meta: list[dict[str, Any]] = field(default_factory=list)
    timings: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationResult:
    text: str
    stats: dict[str, Any] = field(default_factory=dict)


class Retriever(ABC):
    @abstractmethod
    def retrieve(
        self,
        system_name: str,
        question: str,
        model_selection: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        raise NotImplementedError


class Generator(ABC):
    @abstractmethod
    def generate(
        self,
        question: str,
        context: str,
        model_selection: dict[str, Any] | None = None,
    ) -> GenerationResult:
        raise NotImplementedError


class Tool(ABC):
    name: str = "tool"
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError
