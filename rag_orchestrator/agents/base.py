from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class AgentSpec:
    name: str
    system: str | None = None
    tenant: str = "default"
    config: Dict[str, Any] | None = None

class Agent(ABC):
    def __init__(self, spec: AgentSpec) -> None: self.spec = spec
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]: ...