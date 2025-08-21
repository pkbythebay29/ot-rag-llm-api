from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, Any
from .types import ChatMessage, ChatResult

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[ChatMessage], **kw: Any) -> ChatResult: ...
    @abstractmethod
    async def embed(self, texts: Iterable[str], **kw: Any) -> list[list[float]]: ...