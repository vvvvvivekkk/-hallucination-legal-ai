from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

from starlette.concurrency import run_in_threadpool

from ..config import Settings
from ..core.exceptions import ValidationError
from ..core.logger import get_logger
from ..retrieval.hybrid import HybridRetriever
from .citations import build_matcher, extract_citations, payloads_to_chunks
from .confidence import ConfidenceScorer
from .formatter import ResponseFormatter
from .hallucination import HallucinationDetector
from .llm import LLMAdapter, extract_json
from .memory import ConversationMemory
from .models import (
    HallucinationFinding,
    HallucinationReport,
    SourceChunk,
    VerifiedResponse,
)
from .prompts import PromptBuilder
from .ranking import ResponseRanker
from .verification import CitationVerifier


def _ndjson(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False, default=str) + "\n"


class GenerationPipeline:
    """End-to-end generation: retrieval -> prompt -> LLM -> citations ->
    verification -> hallucination detection -> confidence scoring."""

    def __init__(
        self,
        settings: Settings,
        retriever: HybridRetriever,
        llm: LLMAdapter,
        memory: ConversationMemory,
        prompt_builder: PromptBuilder | None = None,
        verifier: CitationVerifier | None = None,
        hallucination: HallucinationDetector | None = None,
        confidence: ConfidenceScorer | None = None,
        ranker: ResponseRanker | None = None,
        formatter: ResponseFormatter | None = None,
        logger: object | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._llm = llm
        self._memory = memory
        self._prompts = prompt_builder or PromptBuilder(
            json_instruction=settings.llm_json_instruction
        )
        self._verifier = verifier or CitationVerifier(
            min_overlap=settings.evidence_min_overlap
        )
        self._hallucination = hallucination or HallucinationDetector(
            claim_threshold=settings.unsupported_claim_threshold,
            contradiction_threshold=settings.evidence_contradiction_threshold,
        )
        self._confidence = confidence or ConfidenceScorer()
        self._ranker = ranker or ResponseRanker()
        self._formatter = formatter or ResponseFormatter()
        self._logger = logger or get_logger(self.__class__.__name__)

    async def _retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None,
        top_k: int | None,
    ) -> list[SourceChunk]:
        results = await run_in_threadpool(
            self._retriever.search,
            query,
            top_k or self._settings.generation_top_k,
            filters,
        )
        return [
            SourceChunk.from_payload(index, result.payload or {})
            for index, result in enumerate(results, start=1)
        ]

    @staticmethod
    def _chunks_from_payloads(payloads: list[dict[str, Any]]) -> list[SourceChunk]:
        return payloads_to_chunks(payloads)

    async def _postprocess(
        self,
        query: str,
        answer: str,
        chunks: list[SourceChunk],
        session_id: str | None = None,
    ) -> VerifiedResponse:
        citations = extract_citations(answer)
        citations = build_matcher(chunks).match(citations)

        verification = (
            self._verifier.verify(query, answer, chunks, citations)
            if self._settings.enable_citation_verification
            else None
        )
        hallucination_report = (
            self._hallucination.detect(query, answer, chunks, citations, verification)
            if self._settings.enable_hallucination_detection
            else None
        )
        if (
            self._settings.enable_llm_verification
            and hallucination_report is not None
            and self._llm.provider != "mock"
        ):
            llm_findings = await self._llm_claim_check(query, answer, chunks)
            hallucination_report.findings.extend(llm_findings)
            hallucination_report.score = round(
                min(1.0, hallucination_report.score + 0.25 * len(llm_findings) / max(1, len(hallucination_report.findings))),
                4,
            )
            hallucination_report.verdict = (
                self._hallucination.verdict_for(hallucination_report.score)
            )

        confidence = (
            self._confidence.score(query, answer, chunks, verification, hallucination_report)
            if self._settings.enable_confidence_scoring
            else None
        )
        return VerifiedResponse(
            query=query,
            answer=answer,
            model=self._llm.model,
            session_id=session_id,
            sources=chunks,
            citations=citations,
            verification=verification,
            hallucination=hallucination_report,
            confidence=confidence,
        )

    async def _llm_claim_check(
        self,
        query: str,
        answer: str,
        chunks: list[SourceChunk],
    ) -> list[HallucinationFinding]:
        try:
            prompt = self._prompts.build_claim_verification_prompt(query, answer, chunks)
            system = self._prompts.build_claim_verifier_system()
            response = await self._llm.generate(prompt, system=system, json_mode=True)
            data = extract_json(response.text) or {}
            unsupported = data.get("unsupported_claims") or []
            return [
                HallucinationFinding(
                    category="unsupported_claim",
                    severity="medium",
                    detail="LLM judge found the claim unsupported by the context",
                    sentence=str(claim) if isinstance(claim, str) else None,
                )
                for claim in unsupported
                if isinstance(claim, str) and claim.strip()
            ]
        except Exception as exc:
            self._logger.warning("LLM claim check failed: %s", exc)
            return []

    async def generate(
        self,
        query: str,
        session_id: str | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
        num_responses: int = 1,
        store_history: bool = True,
    ) -> VerifiedResponse:
        started = time.monotonic()
        chunks = await self._retrieve(query, filters, top_k)
        history = self._memory.messages(session_id) if session_id else None
        system, prompt = self._prompts.build_messages(query, chunks, history)

        if num_responses and num_responses > 1:
            texts = await asyncio.gather(
                *(self._llm.generate(prompt, system=system) for _ in range(num_responses))
            )
            candidates = [
                await self._postprocess(query, response.text, chunks, session_id)
                for response in texts
            ]
            ranked = self._ranker.rank(candidates)
            result = ranked[0] if ranked else await self._postprocess(query, "", chunks, session_id)
        else:
            response = await self._llm.generate(prompt, system=system)
            result = await self._postprocess(query, response.text, chunks, session_id)

        result.elapsed_ms = int((time.monotonic() - started) * 1000)
        if store_history and session_id:
            self._memory.add(session_id, "user", query)
            self._memory.add(session_id, "assistant", result.answer)
        return result

    async def stream(
        self,
        query: str,
        session_id: str | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        started = time.monotonic()
        chunks = await self._retrieve(query, filters, top_k)
        history = self._memory.messages(session_id) if session_id else None
        system, prompt = self._prompts.build_messages(query, chunks, history)
        yield _ndjson({"type": "start", "query": query})

        parts: list[str] = []
        async for token in self._llm.stream(prompt, system=system):
            parts.append(token)
            yield _ndjson({"type": "token", "text": token})

        answer = "".join(parts)
        result = await self._postprocess(query, answer, chunks, session_id)
        result.elapsed_ms = int((time.monotonic() - started) * 1000)
        if session_id:
            self._memory.add(session_id, "user", query)
            self._memory.add(session_id, "assistant", answer)
        yield _ndjson({"type": "result", "result": result.to_dict()})

    async def verify(
        self,
        query: str,
        answer: str,
        context: list[dict[str, Any]] | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> VerifiedResponse:
        chunks = (
            self._chunks_from_payloads(context)
            if context
            else await self._retrieve(query, filters, top_k)
        )
        return await self._postprocess(query, answer, chunks)

    async def citations(
        self,
        query: str,
        answer: str,
        context: list[dict[str, Any]] | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = (
            self._chunks_from_payloads(context)
            if context
            else await self._retrieve(query, filters, top_k)
        )
        citations = extract_citations(answer)
        citations = build_matcher(chunks).match(citations)
        return {
            "query": query,
            "answer": answer,
            "citations": [citation.to_dict() for citation in citations],
            "sources": [chunk.to_dict() for chunk in chunks],
        }

    async def hallucination(
        self,
        query: str,
        answer: str,
        context: list[dict[str, Any]] | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> HallucinationReport:
        chunks = (
            self._chunks_from_payloads(context)
            if context
            else await self._retrieve(query, filters, top_k)
        )
        citations = extract_citations(answer)
        citations = build_matcher(chunks).match(citations)
        return self._hallucination.detect(query, answer, chunks, citations)

    async def confidence(
        self,
        query: str,
        answer: str,
        context: list[dict[str, Any]] | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = (
            self._chunks_from_payloads(context)
            if context
            else await self._retrieve(query, filters, top_k)
        )
        result = await self._postprocess(query, answer, chunks)
        return {
            "query": query,
            "answer": answer,
            "confidence": result.confidence.to_dict() if result.confidence else {},
            "verification": result.verification.to_dict() if result.verification else {},
            "sources": [chunk.to_dict() for chunk in chunks],
        }
