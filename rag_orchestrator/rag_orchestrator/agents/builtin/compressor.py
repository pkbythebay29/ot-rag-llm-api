from __future__ import annotations
from typing import Any, Dict
from ..base import Agent, AgentSpec
from ..registry import register

class CompressorAgent(Agent):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        docs = state.get("retrieved", [])
        # TODO: implement real compression/chunking
        return {"compressed": docs}

@register("compressor")
def factory(spec: AgentSpec): return CompressorAgent(spec)