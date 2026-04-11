from rag_llm_api_pipeline.db import compliance_store, metadata_store, review_store


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
    assert (
        body["response"] == "Dosage guidance requires human validation before release."
    )
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

    authorized = client.get("/review/pending", headers={"x-api-key": "test-review-key"})
    assert authorized.status_code == 200
    assert len(authorized.json()["items"]) == 1


def test_root_ui_explains_hitl_and_audit(app_client):
    client = app_client["client"]

    response = client.get("/")

    assert response.status_code == 200
    assert "Krionis" in response.text
    assert "Workflow" in response.text
    assert "Start Agent" in response.text
    assert "Rebuild Cache" in response.text
    assert "Good" in response.text
    assert "/ui/compliance" in response.text
    assert "/ui/telemetry" in response.text
    assert "/ui/runtime" in response.text
    assert "/ui/configuration" in response.text
    assert "/ui/records" in response.text
    assert "/ui/reviews" in response.text
    assert "controlled query" in response.text.lower()
    assert "/orchestrator/query" in response.text


def test_platform_metadata_and_audit_routes(app_client):
    client = app_client["client"]
    review_id = _submit_flagged_query(client)

    pending = client.get(
        "/review/pending", headers={"x-api-key": "test-review-key"}
    ).json()["items"][0]
    trace_id = pending["trace_id"]

    metadata = client.get("/system/metadata")
    assert metadata.status_code == 200
    assert metadata.json()["system_name"]

    review_lookup = client.get(
        f"/review/{review_id}", headers={"x-api-key": "test-review-key"}
    )
    assert review_lookup.status_code == 200
    assert review_lookup.json()["id"] == review_id

    trace_events = client.get(
        f"/audit/traces/{trace_id}", headers={"x-api-key": "test-review-key"}
    )
    assert trace_events.status_code == 200
    assert trace_events.json()["trace_id"] == trace_id

    review_events = client.get(
        f"/audit/reviews/{review_id}", headers={"x-api-key": "test-review-key"}
    )
    assert review_events.status_code == 200
    assert review_events.json()["review_id"] == review_id

    dashboard = client.get("/platform/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["models"]["llm_model"]
    assert "quantization_backend" in dashboard.json()["models"]
    assert "effective_quantization_backend" in dashboard.json()["models"]
    assert "indexes" in dashboard.json()
    assert "recent_routes" in dashboard.json()
    assert dashboard.json()["recent_routes"][0]["trace_id"] == trace_id
    assert "can_start_another" in dashboard.json()["orchestrator"]["capacity"]

    indexes = client.get("/platform/indexes")
    assert indexes.status_code == 200
    assert indexes.json()["systems"][0]["source_directory"]
    assert indexes.json()["systems"][0]["index_directory"]

    telemetry_snapshot = client.get("/platform/telemetry")
    assert telemetry_snapshot.status_code == 200
    assert telemetry_snapshot.json()["refresh"]["telemetry_refresh_seconds"] >= 1

    configuration = client.get("/platform/configuration")
    assert configuration.status_code == 200
    assert configuration.json()["paths"]["metadata_store"]


def test_quality_feedback_endpoint_records_rating(app_client):
    client = app_client["client"]
    response = client.post(
        "/feedback/quality",
        json={
            "trace_id": "trace-123",
            "rating": "good",
            "system": "TestSystem",
            "question": "Was that good?",
            "response": "Yes.",
        },
        headers={"x-user-id": "operator-1"},
    )
    assert response.status_code == 200
    assert response.json()["rating"] == "good"
    assert response.json()["trace_id"] == "trace-123"

    records = metadata_store.list_records()
    assert any(item["_meta"]["rating"] == "good" for item in records)


def test_orchestrator_routes_are_exposed(app_client):
    client = app_client["client"]

    catalog = client.get("/orchestrator/catalog")
    assert catalog.status_code == 200
    assert any(agent["slug"] == "retriever" for agent in catalog.json()["agents"])
    assert any(agent["slug"] == "regulatory" for agent in catalog.json()["agents"])

    diagnostics = client.get("/orchestrator/diag/agents")
    assert diagnostics.status_code == 200
    assert "registered" in diagnostics.json()

    telemetry = client.get("/orchestrator/telemetry")
    assert telemetry.status_code == 200


def test_platform_agent_lifecycle_routes(app_client):
    client = app_client["client"]

    start = client.post(
        "/platform/agents/start",
        json={
            "system": "TestSystem",
            "agent_type": "retriever",
            "name_prefix": "agent",
        },
    )
    assert start.status_code == 200
    task_id = start.json()["task_id"]

    listed = client.get("/platform/agents")
    assert listed.status_code == 200
    assert any(item["name"] == task_id for item in listed.json()["items"])

    stopped = client.delete(f"/platform/agents/{task_id}")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"


def test_index_rebuild_endpoint_returns_stubbed_report(app_client, monkeypatch):
    from rag_llm_api_pipeline.api import platform_routes

    monkeypatch.setattr(
        platform_routes,
        "rebuild_index_in_worker",
        lambda system_name: {"num_chunks": 3, "system": system_name},
    )

    client = app_client["client"]
    response = client.post("/platform/indexes/TestSystem/rebuild")

    assert response.status_code == 200
    assert response.json()["system_name"] == "TestSystem"
    assert response.json()["report"]["num_chunks"] == 3


def test_observability_pages_load(app_client):
    client = app_client["client"]

    assert client.get("/ui/compliance").status_code == 200
    assert client.get("/ui/telemetry").status_code == 200
    assert client.get("/ui/runtime").status_code == 200
    assert client.get("/ui/configuration").status_code == 200
    assert client.get("/ui/records").status_code == 200


def test_platform_records_endpoint_returns_summary(app_client):
    client = app_client["client"]

    client.post(
        "/feedback/quality",
        json={
            "trace_id": "trace-999",
            "rating": "bad",
            "system": "TestSystem",
            "question": "Was that bad?",
            "response": "No.",
        },
        headers={"x-user-id": "operator-1"},
    )

    records = client.get("/platform/records")
    assert records.status_code == 200
    assert records.json()["summary"]["quality_bad"] >= 1
    assert records.json()["database_path"]


def test_compliance_assessment_enters_review_and_is_stored(app_client):
    client = app_client["client"]

    response = client.post(
        "/compliance/assess",
        json={
            "document_name": "Validation SOP Draft",
            "document_text": "The procedure describes execution steps but does not include validation evidence or approval signatures.",
            "regulation_system": "TestSystem",
            "framework": "EU GMP Annex 11",
            "focus": "Validation",
        },
        headers={"x-user-id": "qa-author-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_review"
    assert body["assessment_id"]
    assert body["review_id"]
    assert body["regulation_system"] == "TestSystem"

    stored = compliance_store.get_assessment(body["assessment_id"])
    assert stored is not None
    assert stored["status"] == "pending_review"
    assert stored["document_name"] == "Validation SOP Draft"
    assert stored["review_id"] == body["review_id"]


def test_compliance_assessment_updates_after_review(app_client):
    client = app_client["client"]

    created = client.post(
        "/compliance/assess",
        json={
            "document_name": "Batch Record Draft",
            "document_text": "The batch record is missing validation evidence and compliance traceability.",
            "regulation_system": "TestSystem",
            "framework": "21 CFR Part 11",
            "focus": "Validation",
        },
        headers={"x-user-id": "qa-author-2"},
    ).json()

    approved = client.post(
        f"/review/{created['review_id']}/approve",
        json={
            "final_response": "Approved compliance assessment after QA review.",
            "reviewer_notes": "Validated against current procedural controls.",
        },
        headers={"x-api-key": "test-review-key", "x-reviewer-id": "qa-lead-1"},
    )

    assert approved.status_code == 200
    stored = compliance_store.get_assessment(created["assessment_id"])
    assert stored is not None
    assert stored["status"] == "approved"
    assert (
        stored["generated_response"]
        == "Approved compliance assessment after QA review."
    )
    assert stored["reviewer_notes"] == "Validated against current procedural controls."


def test_compliance_routes_and_page_return_recent_assessments(app_client):
    client = app_client["client"]

    created = client.post(
        "/compliance/assess",
        json={
            "document_name": "Deviation Form Draft",
            "document_text": "The deviation form references compliance but omits validation signoff.",
        },
    ).json()

    listing = client.get("/compliance/assessments")
    assert listing.status_code == 200
    assert listing.json()["summary"]["total"] >= 1
    assert any(
        item["id"] == created["assessment_id"] for item in listing.json()["items"]
    )

    lookup = client.get(f"/compliance/assessments/{created['assessment_id']}")
    assert lookup.status_code == 200
    assert lookup.json()["document_name"] == "Deviation Form Draft"

    page = client.get("/ui/compliance")
    assert page.status_code == 200
    assert "Compliance Assessment" in page.text
    assert "Run Compliance Check" in page.text
    assert "Regulatory Wire" in page.text


def test_regulation_pool_routes_support_dedicated_pool_and_agent(
    app_client, monkeypatch
):
    client = app_client["client"]

    created = client.post(
        "/compliance/pools",
        json={
            "name": "EURegulations",
            "docs_dir": "data/manuals/regulations",
            "framework": "EU GMP",
            "focus": "Validation",
        },
    )
    assert created.status_code == 200
    assert created.json()["name"] == "EURegulations"
    assert created.json()["agent_type"] == "regulatory"

    listing = client.get("/compliance/pools")
    assert listing.status_code == 200
    assert any(item["name"] == "EURegulations" for item in listing.json()["items"])

    lookup = client.get("/compliance/pools/EURegulations")
    assert lookup.status_code == 200
    assert lookup.json()["framework"] == "EU GMP"

    from rag_llm_api_pipeline.api import compliance_routes

    monkeypatch.setattr(
        compliance_routes,
        "rebuild_index_in_worker",
        lambda pool_name: {"num_chunks": 4, "system": pool_name},
    )

    rebuilt = client.post("/compliance/pools/EURegulations/rebuild")
    assert rebuilt.status_code == 200
    assert rebuilt.json()["report"]["num_chunks"] == 4

    started = client.post("/compliance/pools/EURegulations/start-agent")
    assert started.status_code == 200
    assert started.json()["agent_type"] == "regulatory"
    assert started.json()["system"] == "EURegulations"
