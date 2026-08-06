from __future__ import annotations

from app.retrieval.base import RankedResult


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["qdrant"] == "up"


def test_search_returns_results(client, fake_store) -> None:
    fake_store.results = [
        RankedResult(
            chunk_id="c1",
            score=0.9,
            payload={"doc_id": "d1", "chunk_text": "murder punishment", "summary": "summary"},
            dense_score=0.9,
        )
    ]
    response = client.post("/api/search", json={"query": "what is murder", "top_k": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["chunk_id"] == "c1"
    assert body["results"][0]["summary"] == "summary"


def test_search_validation(client) -> None:
    response = client.post("/api/search", json={"query": ""})
    assert response.status_code == 422


def test_search_with_filters(client, fake_store) -> None:
    fake_store.results = []
    response = client.post(
        "/api/search",
        json={
            "query": "murder",
            "filters": {"courts": ["Supreme Court"], "year_min": 1900, "year_max": 2020},
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_ingest_queues_job(client) -> None:
    response = client.post("/api/ingest", json={"path": "tests"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    job = client.get(f"/api/jobs/{body['job_id']}")
    assert job.status_code == 200
    assert job.json()["status"] == "completed"


def test_ingest_missing_path(client) -> None:
    response = client.post("/api/ingest", json={"path": "/does/not/exist"})
    assert response.status_code == 400


def test_reindex_queues_job(client) -> None:
    response = client.post("/api/reindex", json={"collection": "test"})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_index_queues_job(client) -> None:
    response = client.post("/api/index", json={"collection": "test"})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_get_unknown_job(client) -> None:
    response = client.get("/api/jobs/unknown-id")
    assert response.status_code == 404
