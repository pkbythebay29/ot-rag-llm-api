import json


def test_normal_query_is_auto_approved(app_client):
    client = app_client["client"]
    response = client.post(
        "/query",
        json={"system": "TestSystem", "question": "What is the restart sequence?"},
        headers={"x-user-id": "alice"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert "answer" in body
    assert body["sources"] == ["Chunk 1"]
    assert "runtime" in body

    audit_lines = (
        app_client["audit_log"].read_text(encoding="utf-8").strip().splitlines()
    )
    audit_record = json.loads(audit_lines[-1])
    assert audit_record["status"] == "approved"
    assert audit_record["reviewer_decision"] == "auto_approved"
    assert audit_record["final_approved_response"] == body["answer"]
