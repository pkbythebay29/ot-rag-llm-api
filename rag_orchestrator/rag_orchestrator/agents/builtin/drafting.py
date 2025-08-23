from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register
from ...api._state import batchers


class DraftingAgent(Agent):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            state.get("prompt")
            or state.get("messages", [{"content": ""}])[-1]["content"]
        )
        draft = await batchers.submit("generate", prompt)
        return {"draft": draft}


@register("drafting")
def factory(spec: AgentSpec):
    return DraftingAgent(spec)
