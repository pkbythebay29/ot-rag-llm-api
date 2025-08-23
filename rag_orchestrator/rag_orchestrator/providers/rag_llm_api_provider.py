# rag_orchestrator/providers/rag_llm_api_provider.py
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Any


class RagLLMApiProvider:
    """
    Thin adapter that can talk to rag_llm_api_pipeline regardless of whether it
    exposes a module-level `ask_llm(question, context)` function or a class
    `LLMWrapper` with `.ask(...)` / `.ask_llm(...)`.
    """

    def __init__(self, system_yaml: Path | str) -> None:
        # system_yaml is accepted for parity with other providers,
        # but the current LLM wrapper uses global CONFIG_PATH internally.
        self.system_yaml = Path(system_yaml)

        # Detect & bind an "ask" callable from the pipeline.
        self._ask = self._resolve_ask_callable()

    def _resolve_ask_callable(self):
        try:
            # 1) Preferred: module-level function
            from rag_llm_api_pipeline.llm_wrapper import ask_llm  # type: ignore
            return ask_llm
        except Exception:
            pass

        # 2) Fallback: class with ask()/ask_llm()
        try:
            from rag_llm_api_pipeline.llm_wrapper import LLMWrapper  # type: ignore
            llm = LLMWrapper()
            if hasattr(llm, "ask") and callable(getattr(llm, "ask")):
                return llm.ask
            if hasattr(llm, "ask_llm") and callable(getattr(llm, "ask_llm")):
                return llm.ask_llm
        except Exception as e:
            raise RuntimeError(
                "Could not bind an ask() callable from rag_llm_api_pipeline.llm_wrapper. "
                "Expected `ask_llm(question, context)` or class `LLMWrapper` with "
                "`.ask(...)` / `.ask_llm(...)`."
            ) from e

        raise RuntimeError(
            "LLM wrapper found but did not expose `.ask` or `.ask_llm`."
        )

    def query(self, question: str, context: str = "") -> Tuple[str, dict]:
        """
        Ask the underlying pipeline. Returns (text, stats dict).
        """
        out = self._ask(question, context)  # function may return (text, stats)
        if isinstance(out, tuple) and len(out) == 2:
            text, stats = out
            return str(text or ""), dict(stats or {})
        # Be forgiving: if just text came back
        return str(out or ""), {}
