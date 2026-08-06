from __future__ import annotations

import asyncio

import pytest

from app.config import Settings
from app.generation.llm import LLMConfig, MockLLM
from app.generation.memory import ConversationMemory
from app.generation.pipeline import GenerationPipeline
from app.generation.prompts import PromptBuilder
from app.retrieval.base import RankedResult

CHUNK_1_PAYLOAD = {
    "chunk_id": "chunk-1",
    "doc_id": "doc-1",
    "chunk_text": "The plaintiff must prove negligence by the defendant to recover damages.",
    "doc_title": "Contracts Act",
    "section_number": "12",
    "page": 3,
}
CHUNK_2_PAYLOAD = {
    "chunk_id": "chunk-2",
    "doc_id": "doc-1",
    "chunk_text": "Section 12 requires written consent from both parties.",
    "doc_title": "Contracts Act",
    "section_number": "12",
    "page": 4,
}


class FakeRetriever:
    def __init__(self, results: list[RankedResult] | None = None) -> None:
        self.results = results or [
            RankedResult(chunk_id="chunk-1", score=0.9, payload=CHUNK_1_PAYLOAD),
            RankedResult(chunk_id="chunk-2", score=0.8, payload=CHUNK_2_PAYLOAD),
        ]
        self.calls: list[tuple[str, int | None, dict | None]] = []

    def search(self, query: str, top_k: int | None = None, conditions: dict | None = None):
        self.calls.append((query, top_k, conditions))
        return self.results[: top_k if top_k else len(self.results)]


def _pipeline(retriever: FakeRetriever, llm: MockLLM | None = None) -> GenerationPipeline:
    return GenerationPipeline(
        settings=Settings(),
        retriever=retriever,
        llm=llm or MockLLM(LLMConfig(provider="mock", model="test-model")),
        memory=ConversationMemory(),
        prompt_builder=PromptBuilder(json_instruction=False),
    )


def test_pipeline_generate_grounded_answer_and_stores_history():
    llm = MockLLM(LLMConfig(provider="mock", model="test-model"))

    def handler(prompt, system, json_mode):
        return "The plaintiff must prove negligence by the defendant [1]. Section 12 requires written consent [2]."

    llm.set_handler(handler)
    retriever = FakeRetriever()
    pipeline = _pipeline(retriever, llm)

    result = asyncio.run(pipeline.generate("What must the plaintiff prove?", session_id="s1"))
    assert result.answer.startswith("The plaintiff must prove negligence")
    assert result.model == "test-model"
    assert result.session_id == "s1"
    assert len(result.sources) == 2
    assert len(result.citations) == 2
    assert result.citations[0].verified is True
    assert result.verification.verified_citations == 2
    assert result.verification.grounding_score > 0.5
    assert result.hallucination.verdict == "low"
    assert result.confidence.overall > 0.0
    assert result.elapsed_ms >= 0
    assert len(pipeline._memory.messages("s1")) == 2


def test_pipeline_generate_num_responses_ranks_candidates():
    llm = MockLLM(LLMConfig(provider="mock", model="test-model"))

    def handler(prompt, system, json_mode):
        return "The plaintiff must prove negligence [1]."

    llm.set_handler(handler)
    pipeline = _pipeline(FakeRetriever(), llm)
    result = asyncio.run(pipeline.generate("negligence", num_responses=3))
    assert result.rank == 1
    assert result.quality_score > 0.0


def test_pipeline_stream_yields_ndjson_events():
    llm = MockLLM(LLMConfig(provider="mock", model="test-model"))

    def handler(prompt, system, json_mode):
        return "The plaintiff must prove negligence [1]."

    llm.set_handler(handler)
    pipeline = _pipeline(FakeRetriever(), llm)

    lines = asyncio.run(_collect_stream(pipeline.stream("negligence", session_id="s2")))
    assert lines
    import json

    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["type"] == "start"
    assert any(event["type"] == "token" for event in parsed)
    result_event = next(event for event in parsed if event["type"] == "result")
    assert result_event["result"]["query"] == "negligence"
    assert result_event["result"]["confidence"]["overall"] > 0.0
    assert len(pipeline._memory.messages("s2")) == 2


async def _collect_stream(iterator):
    return [chunk async for chunk in iterator]


def test_pipeline_verify_with_context_payloads():
    pipeline = _pipeline(FakeRetriever())
    result = asyncio.run(
        pipeline.verify(
            "negligence",
            "The plaintiff must prove negligence by the defendant [1].",
            context=[dict(CHUNK_1_PAYLOAD)],
        )
    )
    assert result.verification.total_citations == 1
    assert result.verification.verified_citations == 1


def test_pipeline_citations_hallucination_confidence():
    pipeline = _pipeline(FakeRetriever())
    answer = "The plaintiff must prove negligence by the defendant [1]. Unrelated made up statement."
    citations = asyncio.run(
        pipeline.citations("negligence", answer, context=[dict(CHUNK_1_PAYLOAD)])
    )
    assert citations["citations"][0]["chunk_id"] == "chunk-1"

    report = asyncio.run(
        pipeline.hallucination("negligence", answer, context=[dict(CHUNK_1_PAYLOAD)])
    )
    assert report.findings

    confidence = asyncio.run(
        pipeline.confidence("negligence", answer, context=[dict(CHUNK_1_PAYLOAD)])
    )
    assert confidence["confidence"]["overall"] >= 0.0


def test_pipeline_passes_top_k_and_filters_to_retriever():
    retriever = FakeRetriever()
    pipeline = _pipeline(retriever)
    asyncio.run(pipeline.generate("q", top_k=1, filters={"jurisdiction": "federal"}))
    query, top_k, conditions = retriever.calls[0]
    assert top_k == 1
    assert conditions == {"jurisdiction": "federal"}


def test_pipeline_generation_top_k_default():
    retriever = FakeRetriever()
    pipeline = _pipeline(retriever)
    asyncio.run(pipeline.generate("q"))
    assert retriever.calls[0][1] == pipeline._settings.generation_top_k
