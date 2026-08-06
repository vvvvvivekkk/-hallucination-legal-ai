from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.config import Settings
from app.generation.llm import LLMConfig, MockLLM
from app.generation.memory import ConversationMemory
from app.generation.pipeline import GenerationPipeline
from app.generation.prompts import PromptBuilder
from app.main import app
from app.retrieval.base import RankedResult

CHUNK_PAYLOAD = {
    "chunk_id": "chunk-1",
    "doc_id": "doc-1",
    "chunk_text": "The plaintiff must prove negligence by the defendant to recover damages.",
    "doc_title": "Contracts Act",
    "section_number": "12",
    "page": 3,
}
ANSWER = "The plaintiff must prove negligence by the defendant [1]."


class FakeRetriever:
    def search(self, query: str, top_k: int | None = None, conditions: dict | None = None):
        return [RankedResult(chunk_id="chunk-1", score=0.9, payload=CHUNK_PAYLOAD)]


def _make_llm() -> MockLLM:
    llm = MockLLM(LLMConfig(provider="mock", model="test-model"))

    def handler(prompt, system, json_mode):
        return ANSWER

    llm.set_handler(handler)
    return llm


@pytest.fixture
def gen_client():
    pipeline = GenerationPipeline(
        settings=Settings(),
        retriever=FakeRetriever(),
        llm=_make_llm(),
        memory=ConversationMemory(),
        prompt_builder=PromptBuilder(json_instruction=False),
    )
    app.dependency_overrides.clear()
    app.dependency_overrides[dependencies.get_generation] = lambda: pipeline
    with TestClient(app) as client:
        yield client, pipeline
    app.dependency_overrides.clear()


def test_query_endpoint(gen_client):
    client, _ = gen_client
    response = client.post("/api/query", json={"query": "What must the plaintiff prove?"})
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["answer"] == ANSWER
    assert body["result"]["verification"]["verified_citations"] == 1
    assert body["result"]["confidence"]["overall"] > 0.0
    assert body["result"]["sources"][0]["chunk_id"] == "chunk-1"


def test_query_endpoint_requires_query(gen_client):
    client, _ = gen_client
    assert client.post("/api/query", json={}).status_code == 422


def test_chat_endpoint_non_streaming(gen_client):
    client, _ = gen_client
    response = client.post(
        "/api/chat",
        json={"query": "q", "session_id": "sess-1", "store_history": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["session_id"] == "sess-1"
    assert body["result"]["answer"] == ANSWER


def test_chat_endpoint_streams_ndjson(gen_client):
    client, pipeline = gen_client
    response = client.post(
        "/api/chat",
        json={"query": "q", "session_id": "sess-2", "stream": True},
    )
    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers["content-type"]
    lines = [line for line in response.text.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    assert events[0]["type"] == "start"
    assert any(event["type"] == "token" for event in events)
    result_event = next(event for event in events if event["type"] == "result")
    assert result_event["result"]["answer"] == ANSWER


def test_chat_streaming_rejects_num_responses(gen_client):
    client, _ = gen_client
    response = client.post(
        "/api/chat",
        json={"query": "q", "stream": True, "num_responses": 2},
    )
    assert response.status_code == 400
    assert "num_responses" in response.json()["error"]["message"]


def test_verify_endpoint_with_context(gen_client):
    client, _ = gen_client
    response = client.post(
        "/api/verify",
        json={
            "query": "negligence",
            "answer": ANSWER,
            "context": [CHUNK_PAYLOAD],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["verification"]["verified_citations"] == 1


def test_citations_endpoint_with_context(gen_client):
    client, _ = gen_client
    response = client.post(
        "/api/citations",
        json={"query": "negligence", "answer": ANSWER, "context": [CHUNK_PAYLOAD]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"][0]["chunk_id"] == "chunk-1"


def test_hallucination_endpoint_with_context(gen_client):
    client, _ = gen_client
    response = client.post(
        "/api/hallucination",
        json={
            "query": "negligence",
            "answer": "The plaintiff must prove negligence [1]. The sky is purple and green.",
            "context": [CHUNK_PAYLOAD],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hallucination"]["verdict"] in {"low", "medium", "high"}


def test_confidence_endpoint_with_context(gen_client):
    client, _ = gen_client
    response = client.post(
        "/api/confidence",
        json={"query": "negligence", "answer": ANSWER, "context": [CHUNK_PAYLOAD]},
    )
    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["confidence"]["overall"] <= 1.0


def test_filters_are_translated_to_conditions(gen_client):
    client, pipeline = gen_client

    class CapturingRetriever(FakeRetriever):
        def __init__(self):
            self.last = None

        def search(self, query, top_k=None, conditions=None):
            self.last = conditions
            return super().search(query, top_k, conditions)

    retriever = CapturingRetriever()
    pipeline._retriever = retriever
    client.post(
        "/api/query",
        json={"query": "q", "filters": {"jurisdictions": ["federal"], "pages": [3]}},
    )
    assert retriever.last == {"jurisdiction": ["federal"], "page": [3]}
