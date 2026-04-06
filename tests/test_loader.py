from rag_llm_api_pipeline.db import review_store


def _submit_flagged_query(client):
    response = client.post(
        "/query",
        json={
            "system": "TestSystem",
            "question": "What is the dosage recommendation for this procedure?",
        },
        headers={"x-user-id": "operator-1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending_review"
    return response.json()["review_id"]


def test_risky_query_enters_pending_review(app_client):
    client = app_client["client"]
    review_id = _submit_flagged_query(client)

    item = review_store.get_review(review_id)
    assert item is not None
    assert item["status"] == "pending"
    assert item["query"].startswith("What is the dosage")
    assert item["user_id"] == "operator-1"
    assert item["final_response"] is None


def test_approve_review_stores_final_response(app_client):
    client = app_client["client"]
    review_id = _submit_flagged_query(client)

    response = client.post(
        f"/review/{review_id}/approve",
        json={
            "final_response": "Approved and verified dosage response.",
            "reviewer_notes": "Cross-checked against SOP-17.",
        },
        headers={
            "x-api-key": "test-review-key",
            "x-reviewer-id": "qa-1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["response"] == "Dosage guidance requires human validation before release."
    assert body["final_response"] == "Approved and verified dosage response."
    assert body["reviewer_notes"] == "Cross-checked against SOP-17."

    stored = review_store.get_review(review_id)
    assert stored["response"] == body["response"]
    assert stored["final_response"] == body["final_response"]


def test_reject_review_stores_notes(app_client):
    client = app_client["client"]
    review_id = _submit_flagged_query(client)

    response = client.post(
        f"/review/{review_id}/reject",
        json={"reviewer_notes": "Insufficient evidence for release."},
        headers={
            "x-api-key": "test-review-key",
            "x-reviewer-id": "qa-2",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["reviewer_notes"] == "Insufficient evidence for release."

    stored = review_store.get_review(review_id)
    assert stored["status"] == "rejected"
    assert stored["reviewer_notes"] == "Insufficient evidence for release."


def test_review_dashboard_loads_and_renders_pending_item(app_client):
    client = app_client["client"]
    _submit_flagged_query(client)

    response = client.get("/ui/reviews", headers={"x-api-key": "test-review-key"})

    assert response.status_code == 200
    assert "Review Dashboard" in response.text
    assert "dosage recommendation" in response.text.lower()


def test_pending_review_endpoint_requires_api_key(app_client):
    client = app_client["client"]
    _submit_flagged_query(client)

    unauthorized = client.get("/review/pending")
    assert unauthorized.status_code == 401

    authorized = client.get(
        "/review/pending", headers={"x-api-key": "test-review-key"}
    )
    assert authorized.status_code == 200
    assert len(authorized.json()["items"]) == 1


def test_root_ui_explains_hitl_and_audit(app_client):
    client = app_client["client"]

    response = client.get("/")

    assert response.status_code == 200
    assert "Krionis HITL RAG" in response.text
    assert "/ui/reviews" in response.text
    assert "mandatory review" in response.text.lower()
