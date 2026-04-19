from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from rag_orchestrator.agents.base import AgentSpec, Agent
from rag_orchestrator.agents import registry as agent_registry


@dataclass
class AgentHandle:
    agent_id: str
    agent_type: str
    spec: AgentSpec
    agent: Agent

    @property
    def id(self) -> str:
        return self.agent_id

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def ready(self) -> bool:
        return True

    @property
    def system(self) -> str | None:
        return self.spec.system


class AgentManager:
    def __init__(self) -> None:
        self._agents: Dict[str, AgentHandle] = {}
        self._lock = asyncio.Lock()

    async def create(self, agent_type: str, spec: AgentSpec) -> AgentHandle:
        agent = agent_registry.create(agent_type, spec)
        await agent.start()
        h = AgentHandle(str(uuid.uuid4()), agent_type, spec, agent)
        async with self._lock:
            self._agents[h.agent_id] = h
        return h

    async def destroy(self, agent_id: str) -> None:
        async with self._lock:
            h = self._agents.pop(agent_id, None)
        if h:
            try:
                await h.agent.stop()
            except Exception:
                pass

    async def list(self) -> list[dict]:
        async with self._lock:
            return [
                {
                    "id": a.agent_id,
                    "type": a.agent_type,
                    "name": a.spec.name,
                    "tenant": a.spec.tenant,
                    "system": a.spec.system,
                    "config": dict(a.spec.config or {}),
                }
                for a in self._agents.values()
            ]

    async def step(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        async with self._lock:
            h = self._agents.get(agent_id)
        if not h:
            raise KeyError(agent_id)
        return await h.agent.step(state)

    @property
    def handles(self) -> Dict[str, AgentHandle]:
        return self._agents
