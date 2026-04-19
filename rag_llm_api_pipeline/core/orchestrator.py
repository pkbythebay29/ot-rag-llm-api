from __future__ import annotations

from typing import Any

from rag_llm_api_pipeline.core.tools import DocumentSearchTool


class PlaceholderOrchestrator:
    """
    Future orchestration hook.

    For now it routes directly to the existing RAG pipeline wrapped as a tool,
    which keeps the query flow backward compatible while opening a clean path
    to agent selection and tool routing later.
    """

    def __init__(self, document_search_tool: DocumentSearchTool | None = None) -> None:
        self.document_search_tool = document_search_tool or DocumentSearchTool()

    def run_query(
        self,
        system_name: str,
        question: str,
        model_selection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.document_search_tool.run(
            system_name=system_name,
            question=question,
            model_selection=model_selection,
        )


def get_orchestrator() -> PlaceholderOrchestrator:
    return PlaceholderOrchestrator()
