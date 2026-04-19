from pathlib import Path
from shutil import copyfile

import pytest
from fastapi.testclient import TestClient


class FakeOrchestrator:
    def run_query(
        self,
        system_name: str,
        question: str,
        model_selection: dict | None = None,
    ) -> dict:
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
            "runtime": dict(model_selection or {}),
        }


@pytest.fixture()
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source_config = Path(__file__).resolve().parent.parent / "config" / "system.yaml"
    runtime_config_dir = tmp_path / "config"
    runtime_config_dir.mkdir(parents=True, exist_ok=True)
    runtime_config_path = runtime_config_dir / "system.yaml"
    copyfile(source_config, runtime_config_path)

    monkeypatch.setenv("KRIONIS_CONFIG_PATH", str(runtime_config_path))
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
