from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register


class RetrieverAgent(Agent):
    def __init__(self, spec: AgentSpec):
        super().__init__(spec)

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = (
            state.get("query")
            or state.get("messages", [{"content": ""}])[-1]["content"]
        )
        # TODO: call your pipeline's retrieval (FAISS/HNSW) via provider
        return {"retrieved": [{"text": query, "score": 1.0}]}


@register("retriever")
def factory(spec: AgentSpec):
    return RetrieverAgent(spec)
