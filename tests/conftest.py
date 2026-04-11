from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class FakeOrchestrator:
    def run_query(self, system_name: str, question: str) -> dict:
        normalized = question.lower()
        if "compliance" in normalized:
            answer = "Compliance gap detected: validation evidence is missing."
        elif "dosage" in normalized:
            answer = "Dosage guidance requires human validation before release."
        else:
            answer = "The restart sequence begins by isolating the power source."

        return {
            "system": system_name,
            "question": question,
            "answer": answer,
            "sources": ["Chunk 1"],
            "retrieved_documents": [{"file": "manual.txt", "rank": 1}],
            "stats": {
                "query_time_sec": 0.12,
                "gen_time_sec": 0.05,
                "gen_tokens": 12,
                "tokens_per_sec": 240.0,
                "retrieval": {"faiss_search_sec": 0.01},
                "chunks_meta": [{"file": "manual.txt", "rank": 1}],
            },
        }


@pytest.fixture()
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KRIONIS_REVIEW_API_KEY", "test-review-key")
    monkeypatch.setenv("KRIONIS_REVIEW_DB_PATH", str(tmp_path / "reviews.sqlite3"))
    monkeypatch.setenv(
        "KRIONIS_AUDIT_LOG_PATH", str(tmp_path / "audit" / "audit_log.jsonl")
    )
    monkeypatch.setenv(
        "KRIONIS_FEEDBACK_LOG_PATH",
        str(tmp_path / "feedback" / "corrections.jsonl"),
    )
    monkeypatch.setenv(
        "KRIONIS_QUALITY_LOG_PATH",
        str(tmp_path / "feedback" / "quality_ratings.jsonl"),
    )
    monkeypatch.setenv(
        "KRIONIS_RESULTS_DB_PATH",
        str(tmp_path / "feedback" / "result_metadata.sqlite3"),
    )
    monkeypatch.setenv(
        "KRIONIS_COMPLIANCE_DB_PATH",
        str(tmp_path / "compliance" / "assessments.sqlite3"),
    )
    monkeypatch.setenv(
        "KRIONIS_REGULATION_POOL_DB_PATH",
        str(tmp_path / "compliance" / "regulation_pools.sqlite3"),
    )
    monkeypatch.setenv("KRIONIS_DISABLE_QUERY_WORKER", "1")

    import rag_llm_api_pipeline.core.controlled as controlled
    import rag_llm_api_pipeline.api.server as server

    monkeypatch.setattr(controlled, "get_orchestrator", lambda: FakeOrchestrator())

    return {
        "client": TestClient(server.app),
        "audit_log": tmp_path / "audit" / "audit_log.jsonl",
    }
