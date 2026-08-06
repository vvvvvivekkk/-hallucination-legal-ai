from __future__ import annotations

from typing import Any

from .models import VerifiedResponse


class ResponseFormatter:
    """Renders verified responses as JSON dicts or Markdown documents."""

    def format_json(self, response: VerifiedResponse) -> dict[str, Any]:
        return response.to_dict()

    def format_markdown(self, response: VerifiedResponse) -> str:
        sections: list[str] = [response.answer.strip()]

        if response.citations:
            references = ["## Sources"]
            seen: set[str] = set()
            for citation in response.citations:
                source = next(
                    (item for item in response.sources if item.index == citation.index),
                    None,
                )
                if source is None:
                    continue
                key = source.chunk_id
                if key in seen:
                    continue
                seen.add(key)
                label = source.doc_title or source.source_file or "Source"
                meta: list[str] = []
                if source.section_number or source.section:
                    meta.append(" ".join(
                        part for part in (source.section_number, source.section) if part
                    ))
                if source.page is not None:
                    meta.append(f"p. {source.page}")
                suffix = f" ({'; '.join(meta)})" if meta else ""
                status = "verified" if citation.supported else "unverified"
                references.append(
                    f"{citation.index}. {label}{suffix} — {status}"
                    f" (evidence {citation.evidence_score:.2f})"
                )
            sections.append("\n".join(references))

        verification = response.verification
        hallucination = response.hallucination
        confidence = response.confidence
        if verification or hallucination or confidence:
            summary = ["## Verification"]
            if verification is not None:
                summary.append(
                    f"- Citations: {verification.verified_citations}/{verification.total_citations} verified "
                    f"| grounding {verification.grounding_score:.2f}"
                )
                if verification.missing_citations:
                    summary.append(
                        f"- Missing references: {verification.missing_citations}"
                    )
            if hallucination is not None:
                summary.append(
                    f"- Hallucination risk: {hallucination.verdict}"
                    f" (score {hallucination.score:.2f}, {len(hallucination.findings)} findings)"
                )
            if confidence is not None:
                summary.append(f"- Confidence: {self._bar(confidence.overall)} {confidence.overall:.2f}")
            sections.append("\n".join(summary))

        return "\n\n".join(sections)

    @staticmethod
    def _bar(value: float) -> str:
        filled = round(max(0.0, min(1.0, value)) * 10)
        return "█" * filled + "░" * (10 - filled)
