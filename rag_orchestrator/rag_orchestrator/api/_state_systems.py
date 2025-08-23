from __future__ import annotations
from typing import Dict
from .config_bridge import resolve_system_yaml
from ..providers.rag_llm_api_provider import RagLLMApiProvider


class ProviderPool:
    def __init__(self, systems_root: str, fallback_yaml: str):
        self.systems_root = systems_root
        self.fallback_yaml = fallback_yaml
        self.cache: Dict[str, RagLLMApiProvider] = {}

    def get(self, system: str | None):
        path = resolve_system_yaml(system, self.systems_root, self.fallback_yaml)
        if path in self.cache:
            return self.cache[path]
        prov = RagLLMApiProvider(path)  # raises if pipeline missing
        self.cache[path] = prov
        return prov
