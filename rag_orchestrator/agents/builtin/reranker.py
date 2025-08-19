from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register

class RerankerAgent(Agent):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        items = state.get("retrieved") or state.get("compressed") or []
        # TODO: call cross-encoder to rerank
        return {"reranked": items}

@register("reranker")
def factory(spec: AgentSpec): return RerankerAgent(spec)