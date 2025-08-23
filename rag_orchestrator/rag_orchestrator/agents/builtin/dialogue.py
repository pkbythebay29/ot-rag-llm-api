from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register
from ...api._state import batchers

class DialogueAgent(Agent):
    def __init__(self, spec: AgentSpec):
        super().__init__(spec); self._memory: list[Dict[str,str]] = []
    async def start(self) -> None: ...
    async def stop(self) -> None: self._memory.clear()
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        msgs = state.get("messages", [])
        self._memory.extend(msgs)
        prompt = "\n".join(m.get("content","") for m in self._memory[-8:])
        out = await batchers.submit("generate", prompt)
        return {"answer": out, "memory_len": len(self._memory)}

@register("dialogue")
def factory(spec: AgentSpec): return DialogueAgent(spec)