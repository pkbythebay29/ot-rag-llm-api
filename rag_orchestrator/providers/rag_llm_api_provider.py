from __future__ import annotations
from typing import Any, Iterable
from ..core.types import ChatMessage, ChatResult
from ..api.imports import is_installed

class MissingRagPipeline(RuntimeError):
    def __init__(self):
        super().__init__("rag_llm_api_pipeline not installed. Run: pip install rag-llm-api-pipeline")

class RagLLMApiProvider:
    def __init__(self, system_yaml_path: str):
        if not is_installed("rag_llm_api_pipeline"):
            raise MissingRagPipeline()
        from rag_llm_api_pipeline.config_loader import load_config
        from rag_llm_api_pipeline.llm_wrapper import LLMWrapper
        self.cfg = load_config(system_yaml_path)
        self.llm = LLMWrapper(self.cfg)

    async def chat(self, messages: list[ChatMessage], **kw: Any) -> ChatResult:
        text = await self.llm.generate(messages=messages, **kw)
        return {"text": text}

    async def embed(self, texts: Iterable[str], **kw: Any) -> list[list[float]]:
        if hasattr(self.llm, "embed"):
            return await self.llm.embed(list(texts), **kw)
        return [[float(len(t))] for t in texts]

    async def forward_batch(self, prompts: list[str]) -> list[str]:
        if hasattr(self.llm, "generate_batch"):
            return await self.llm.generate_batch(prompts)
        outs = []
        for p in prompts:
            outs.append(await self.llm.generate(messages=[{"role":"user","content":p}]))
        return outs