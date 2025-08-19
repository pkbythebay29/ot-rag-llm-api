from __future__ import annotations
from typing import Callable, Dict
from importlib.metadata import entry_points
from .base import Agent, AgentSpec

_registry: Dict[str, Callable[[AgentSpec], Agent]] = {}

def register(name: str):
    def deco(factory: Callable[[AgentSpec], Agent]):
        _registry[name] = factory; return factory
    return deco

def load_entry_points():
    try:
        for ep in entry_points(group="rag_orchestrator.agents"):
            _registry.setdefault(ep.name, ep.load())
    except Exception:
        pass

def create(agent_type: str, spec: AgentSpec) -> Agent:
    if agent_type not in _registry: load_entry_points()
    if agent_type not in _registry: raise ValueError(f"Unknown agent type '{agent_type}'")
    return _registry[agent_type](spec)

def list_types() -> list[str]:
    load_entry_points(); return sorted(_registry.keys())