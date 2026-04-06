from __future__ import annotations

import time
from typing import Any

from rag_llm_api_pipeline.core.interfaces import (
    GenerationResult,
    Generator,
    RetrievalResult,
    Retriever,
    Tool,
)


class LegacyRetrieverAdapter(Retriever):
    """Adapter around the existing retrieval code path."""

    def retrieve(self, system_name: str, question: str) -> RetrievalResult:
        from rag_llm_api_pipeline.retriever import _retrieve_chunks

        chunks, context, chunks_meta, timings = _retrieve_chunks(system_name, question)
        return RetrievalResult(
            question=question,
            chunks=list(chunks),
            context=context,
            chunks_meta=list(chunks_meta),
            timings=dict(timings),
        )


class LegacyGeneratorAdapter(Generator):
    """Adapter around the existing generation code path."""

    def generate(self, question: str, context: str) -> GenerationResult:
        from rag_llm_api_pipeline.llm_wrapper import ask_llm

        text, stats = ask_llm(question, context)
        return GenerationResult(text=text, stats=dict(stats))


class DocumentSearchTool(Tool):
    name = "document_search"
    description = "Run the existing RAG retrieval and generation flow as a tool."

    def __init__(
        self,
        retriever: Retriever | None = None,
        generator: Generator | None = None,
    ) -> None:
        self.retriever = retriever or LegacyRetrieverAdapter()
        self.generator = generator or LegacyGeneratorAdapter()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        system_name = str(kwargs["system_name"])
        question = str(kwargs["question"])

        started_at = time.perf_counter()
        retrieval = self.retriever.retrieve(system_name, question)
        generation = self.generator.generate(question, retrieval.context)
        total_sec = round(time.perf_counter() - started_at, 4)

        stats = {
            "query_time_sec": total_sec,
            **generation.stats,
            "retrieval": retrieval.timings,
            "chunks_meta": retrieval.chunks_meta,
        }
        return {
            "system": system_name,
            "question": question,
            "answer": generation.text,
            "sources": retrieval.chunks,
            "retrieved_documents": retrieval.chunks_meta,
            "stats": stats,
        }
