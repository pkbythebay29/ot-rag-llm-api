from __future__ import annotations
import asyncio, uuid
from dataclasses import dataclass
from typing import Any, Dict
from ..agents.base import AgentSpec, Agent
from ..agents import registry as agent_registry

@dataclass
class AgentHandle:
    agent_id: str; agent_type: str; spec: AgentSpec; agent: Agent

class AgentManager:
    def __init__(self) -> None:
        self._agents: Dict[str, AgentHandle] = {}
        self._lock = asyncio.Lock()
    async def create(self, agent_type: str, spec: AgentSpec) -> AgentHandle:
        agent = agent_registry.create(agent_type, spec)
        await agent.start()
        h = AgentHandle(str(uuid.uuid4()), agent_type, spec, agent)
        async with self._lock: self._agents[h.agent_id] = h
        return h
    async def destroy(self, agent_id: str) -> None:
        async with self._lock: h = self._agents.pop(agent_id, None)
        if h: 
            try: await h.agent.stop()
            except Exception: pass
    async def list(self) -> list[dict]:
        async with self._lock:
            return [{"id":a.agent_id,"type":a.agent_type,"name":a.spec.name,"tenant":a.spec.tenant} for a in self._agents.values()]
    async def step(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        async with self._lock: h = self._agents.get(agent_id)
        if not h: raise KeyError(agent_id)
        return await h.agent.step(state)