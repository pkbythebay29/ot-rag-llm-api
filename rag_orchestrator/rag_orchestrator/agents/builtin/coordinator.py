from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register


class CoordinatorAgent(Agent):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: orchestrate sub-steps (quantization, batching strategy, presets)
        return {"coordinated": True}


@register("coordinator")
def factory(spec: AgentSpec):
    return CoordinatorAgent(spec)
