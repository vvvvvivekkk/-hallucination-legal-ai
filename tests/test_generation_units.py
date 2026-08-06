from __future__ import annotations

import asyncio

import pytest

from app.generation.citations import (
    CitationMatcher,
    build_matcher,
    citation_indices_in_sentence,
    extract_citations,
    parse_indices,
    payloads_to_chunks,
)
from app.generation.confidence import ConfidenceScorer
from app.generation.formatter import ResponseFormatter
from app.generation.hallucination import HallucinationDetector
from app.generation.llm import (
    LLMConfig,
    LLMResponse,
    MockLLM,
    SSEParser,
    build_llm,
    extract_json,
)
from app.generation.memory import ConversationMemory, ConversationTurn
from app.generation.models import (
    Citation,
    HallucinationFinding,
    HallucinationReport,
    SourceChunk,
    VerificationReport,
    VerifiedResponse,
)
from app.generation.prompts import PromptBuilder
from app.generation.ranking import ResponseRanker
from app.generation.text import (
    best_containment,
    clamp,
    containment,
    mean,
    overlap,
    sentences,
    significant_tokens,
    tokenize,
)
from app.generation.verification import CitationVerifier


def _chunk(index: int, text: str, section_number: str | None = None) -> SourceChunk:
    return SourceChunk(
        index=index,
        chunk_id=f"chunk-{index}",
        doc_id="doc-1",
        text=text,
        score=0.9,
        doc_title="Contracts Act",
        section_number=section_number,
        page=index,
    )


def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("The Offer; ACCEPTANCE, 1999!") == ["the", "offer", "acceptance", "1999"]


def test_significant_tokens_filters_stopwords_and_digits():
    tokens = significant_tokens("the parties must sign the contract on page 12")
    assert "the" not in tokens
    assert "contract" in tokens
    assert "sign" in tokens
    assert "12" not in tokens
    assert all(len(t) > 1 for t in tokens)


def test_sentences_splits_on_punctuation():
    assert sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]


def test_overlap_dice():
    assert overlap(["a", "b"], ["a", "b"]) == 1.0
    assert overlap(["a", "b"], ["b", "c"]) == 0.5
    assert overlap([], ["a"]) == 0.0


def test_containment_proportion_of_inner_tokens():
    assert containment(["a", "b", "c"], ["a", "b", "x"]) == pytest.approx(round(2 / 3, 4))
    assert containment([], ["a"]) == 0.0


def test_best_containment_takes_max():
    inner = ["a", "b"]
    assert best_containment(inner, [["x", "y"], ["a", "b", "c"]]) == 1.0
    assert best_containment(inner, []) == 0.0


def test_clamp_and_mean():
    assert clamp(1.5) == 1.0
    assert clamp(-0.5) == 0.0
    assert clamp(0.5) == 0.5
    assert mean([1.0, 2.0]) == 1.5
    assert mean([]) == 0.0


def test_parse_indices_single_and_ranges():
    assert parse_indices("1") == [1]
    assert parse_indices("1,3,5") == [1, 3, 5]
    assert parse_indices("2-4") == [2, 3, 4]
    assert parse_indices("4-2") == [4, 3, 2]
    assert parse_indices("1, 3-5") == [1, 3, 4, 5]


def test_extract_citations_dedupes_and_caps_index():
    answer = "See [1] and [2,4] and again [1]. Also [3-5]."
    citations = extract_citations(answer)
    assert [c.index for c in citations] == [1, 2, 4, 3, 5]
    assert extract_citations("bogus [0] and [100]") == []


def test_citation_indices_in_sentence():
    assert citation_indices_in_sentence("The rule in [1,3] applies.") == [1, 3]


def test_payloads_to_chunks_uses_enumerated_indices():
    chunks = payloads_to_chunks([{"chunk_id": "a", "chunk_text": "x"}, {"chunk_id": "b", "chunk_text": "y"}])
    assert [c.index for c in chunks] == [1, 2]
    assert chunks[0].chunk_id == "a"


def test_citation_matcher_maps_markers_to_chunks():
    chunks = [_chunk(1, "text"), _chunk(2, "text")]
    matcher = CitationMatcher(chunks)
    citations = matcher.match([Citation(1, "[1]", 0, 3), Citation(9, "[9]", 0, 3)])
    assert citations[0].verified is True
    assert citations[0].chunk_id == "chunk-1"
    assert citations[1].verified is False
    assert citations[1].reason == "no matching source chunk"
    assert build_matcher(chunks).max_index == 2


def test_conversation_memory_roundtrip_and_pruning():
    memory = ConversationMemory(max_turns=3, max_chars=1000, max_sessions=2)
    memory.add("s1", "user", "hello")
    turn = memory.add("s1", "assistant", "hi there")
    assert isinstance(turn, ConversationTurn)
    assert memory.messages("s1") == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    memory.add("s1", "user", "a")
    memory.add("s1", "assistant", "b")
    memory.add("s1", "user", "c")
    assert len(memory.get("s1")) == 3
    assert memory.messages("s1")[0] == {"role": "user", "content": "a"}
    assert memory.session_count() == 1
    memory.clear("s1")
    assert memory.get("s1") == []


def test_conversation_memory_rejects_invalid_input():
    memory = ConversationMemory()
    with pytest.raises(ValueError):
        memory.add("s1", "user", "")
    with pytest.raises(ValueError):
        memory.add("s1", "system", "x")


def test_conversation_memory_evicts_oldest_sessions():
    memory = ConversationMemory(max_sessions=2)
    memory.add("s1", "user", "a")
    memory.add("s2", "user", "b")
    memory.add("s3", "user", "c")
    memory.add("s4", "user", "d")
    assert memory.session_count() == 2
    assert memory.get("s1") == []
    assert memory.get("s2") == []
    assert memory.get("s3") and memory.get("s4")


def test_prompt_builder_includes_context_and_conversation():
    builder = PromptBuilder()
    chunks = [_chunk(1, "The offer is valid.", "12")]
    system, prompt = builder.build_messages("Is the offer valid?", chunks)
    assert "legal research assistant" in system
    assert "[1]" in prompt
    assert "### CONTEXT" in prompt
    assert "Section: 12" in prompt
    assert "(no prior conversation)" in prompt

    history = [{"role": "user", "content": "previous question"}]
    system, prompt = builder.build_messages("next", chunks, history, json_mode=True)
    assert "JSON object" in system
    assert "previous question" in prompt


def test_prompt_builder_claim_verification_prompt():
    builder = PromptBuilder()
    chunks = [_chunk(1, "evidence text")]
    prompt = builder.build_claim_verification_prompt("q", "answer", chunks)
    assert "unsupported_claims" in builder.build_claim_verifier_system()
    assert "answer" in prompt


def test_extract_json_parses_plain_fenced_and_embedded():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here is the answer: {"nested": {"x": [1, 2]}} thanks') == {
        "nested": {"x": [1, 2]}
    }
    assert extract_json(None) is None
    assert extract_json("no json here") is None


def test_sse_parser_groups_multiline_data():
    parser = SSEParser()
    assert parser.push_line("event: foo") == []
    assert parser.push_line("data: line1") == []
    assert parser.push_line("data: line2") == []
    assert parser.push_line("") == [("foo", "line1\nline2")]
    assert parser.push_line("data: [DONE]") == []
    assert parser.flush() == [("message", "[DONE]")]


def test_mock_llm_generate_and_stream_with_handler():
    config = LLMConfig(provider="mock", model="mock-model")
    llm = MockLLM(config)

    def handler(prompt, system, json_mode):
        return f"echo:{prompt[:3]}"

    llm.set_handler(handler)
    assert asyncio.run(llm.generate("hello world")) == LLMResponse(
        text="echo:hel", provider="mock", model="mock-model"
    )
    assert "hello world" in llm.seen_prompts

    streamed = asyncio.run(_collect(llm.stream("abcdefghij")))
    assert "".join(streamed) == "echo:abc"

    llm.set_handler(None)
    config.mock_response = "canned"
    assert asyncio.run(llm.generate("x")).text == "canned"


async def _collect(iterator):
    return [item async for item in iterator]


def test_build_llm_returns_correct_adapter():
    assert isinstance(build_llm(LLMConfig(provider="mock")), MockLLM)
    with pytest.raises(Exception):
        build_llm(LLMConfig(provider="nope"))


def test_verifier_supported_and_unsupported_citations():
    chunks = [
        _chunk(1, "The plaintiff must prove negligence by the defendant."),
        _chunk(2, "Section 12 requires written consent."),
    ]
    answer = "The plaintiff must prove negligence by the defendant [1]. Section 12 requires written consent [2]."
    citations = extract_citations(answer)
    citations = build_matcher(chunks).match(citations)
    report = CitationVerifier(min_overlap=0.15).verify("negligence", answer, chunks, citations)
    assert report.total_citations == 2
    assert report.verified_citations == 2
    assert report.grounding_score > 0.5
    assert report.missing_citations == []
    for check in report.checks:
        assert check.supported is True

    unsupported = CitationVerifier(min_overlap=0.15).verify(
        "q", "The moon is made of cheese [1].", chunks, extract_citations("The moon is made of cheese [1].")
    )
    assert unsupported.checks[0].supported is False


def test_verifier_reports_missing_reference():
    chunks = [_chunk(1, "text")]
    report = CitationVerifier().verify(
        "q", "Some claim [7].", chunks, extract_citations("Some claim [7].")
    )
    assert report.missing_citations == [7]
    assert report.verified_citations == 0


def test_hallucination_detector_flags_uncited_and_contradictory():
    chunks = [_chunk(1, "The court denied the appeal.")]
    answer = "The judge awarded a million dollars. The court never denied the appeal [1]."
    citations = extract_citations(answer)
    citations = build_matcher(chunks).match(citations)
    report = HallucinationDetector().detect("appeal", answer, chunks, citations)
    categories = {finding.category for finding in report.findings}
    assert "missing_evidence" in categories
    assert "contradicting_evidence" in categories
    assert report.verdict in {"low", "medium", "high"}


def test_hallucination_detector_contradiction_and_verdict_for():
    assert HallucinationDetector.verdict_for(0.6) == "high"
    assert HallucinationDetector.verdict_for(0.3) == "medium"
    assert HallucinationDetector.verdict_for(0.1) == "low"


def test_confidence_scorer_returns_bounded_metrics():
    chunks = [_chunk(1, "The offer is valid and binding.")]
    report = ConfidenceScorer().score("Is the offer valid?", "The offer is valid [1].", chunks)
    for value in (
        report.faithfulness,
        report.answer_relevance,
        report.context_precision,
        report.context_recall,
        report.overall,
    ):
        assert 0.0 <= value <= 1.0
    assert report.overall > 0.0


def test_response_ranker_orders_candidates():
    chunks = [_chunk(1, "text")]
    base = {
        "query": "q",
        "answer": "answer",
        "sources": chunks,
        "citations": [Citation(1, "[1]", 0, 3, evidence_score=0.8)],
        "verification": VerificationReport(
            checks=[], grounding_score=0.8, verified_citations=1, total_citations=1
        ),
        "hallucination": HallucinationReport(score=0.1, verdict="low"),
    }
    good = ConfidenceScorer().score("q", "good answer grounded in text", chunks)
    bad = ConfidenceScorer().score("q", "totally unrelated rambling nonsense about nothing", chunks)
    ranker = ResponseRanker()
    ranked = ranker.rank(
        [
            type("C", (), {**base, "confidence": bad, "quality_score": 0.0, "rank": None})(),
            type("C", (), {**base, "confidence": good, "quality_score": 0.0, "rank": None})(),
        ]
    )
    assert ranked[0].rank == 1
    assert ranked[0].quality_score >= ranked[1].quality_score


def test_formatter_json_and_markdown():
    chunks = [_chunk(1, "The offer is valid.", "12")]
    response = VerifiedResponse(
        query="q",
        answer="The offer is valid [1].",
        model="m",
        elapsed_ms=10,
        quality_score=0.8,
        rank=1,
        sources=chunks,
        citations=[Citation(1, "[1]", 0, 3, chunk_id="chunk-1", verified=True, supported=True, evidence_score=0.9)],
        verification=VerificationReport(grounding_score=0.9, verified_citations=1, total_citations=1),
        hallucination=HallucinationReport(score=0.1, verdict="low"),
        confidence=ConfidenceScorer().score("q", "The offer is valid.", chunks),
    )
    formatter = ResponseFormatter()
    data = formatter.format_json(response)
    assert data["query"] == "q"
    assert data["verification"]["grounding_score"] == 0.9
    md = formatter.format_markdown(response)
    assert "## Sources" in md
    assert "## Verification" in md
    assert "verified" in md
    assert "█" in md or "░" in md
