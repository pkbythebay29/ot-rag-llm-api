from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register
from ...api._state import batchers

class ValidatorAgent(Agent):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        draft = state.get("draft") or ""
        validated = await batchers.submit("validate", draft)
        return {"answer": validated}

@register("validator")
def factory(spec: AgentSpec): return ValidatorAgent(spec)