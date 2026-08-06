from __future__ import annotations

import re
from typing import Any

from .models import Citation, SourceChunk

_MARKER_RE = re.compile(r"\[(\d{1,2}(?:\s*[,;]\s*\d{1,2}|\s*[-–]\s*\d{1,2})*)\]")
_RANGE_RE = re.compile(r"(\d{1,2})\s*[-–]\s*(\d{1,2})")

MAX_CITATION_INDEX = 99


def parse_indices(group: str) -> list[int]:
    indices: list[int] = []
    for part in re.split(r"\s*[,;]\s*", group.strip()):
        if not part:
            continue
        range_match = _RANGE_RE.fullmatch(part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            step = 1 if start <= end else -1
            indices.extend(range(start, end + step, step))
        else:
            indices.append(int(part))
    return indices


def extract_citations(answer: str) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[int] = set()
    for match in _MARKER_RE.finditer(answer):
        marker = match.group(0)
        start, end = match.start(), match.end()
        for index in parse_indices(match.group(1)):
            if index < 1 or index > MAX_CITATION_INDEX or index in seen:
                continue
            seen.add(index)
            citations.append(
                Citation(index=index, marker=marker, start=start, end=end)
            )
    return citations


def citation_indices_in_sentence(sentence: str) -> list[int]:
    indices: list[int] = []
    for match in _MARKER_RE.finditer(sentence):
        indices.extend(parse_indices(match.group(1)))
    return sorted(set(index for index in indices if 1 <= index <= MAX_CITATION_INDEX))


class CitationMatcher:
    """Maps citation markers to the retrieved source chunks."""

    def __init__(self, chunks: list[SourceChunk]) -> None:
        self._by_index = {chunk.index: chunk for chunk in chunks}

    @property
    def max_index(self) -> int:
        return max(self._by_index, default=0)

    def match(self, citations: list[Citation]) -> list[Citation]:
        for citation in citations:
            chunk = self._by_index.get(citation.index)
            if chunk is not None:
                citation.chunk_id = chunk.chunk_id
                citation.verified = True
                citation.reason = "reference found"
            else:
                citation.chunk_id = None
                citation.verified = False
                citation.reason = "no matching source chunk"
        return citations


def build_matcher(chunks: list[SourceChunk]) -> CitationMatcher:
    return CitationMatcher(chunks)


def payloads_to_chunks(payloads: list[dict[str, Any]]) -> list[SourceChunk]:
    return [
        SourceChunk.from_payload(index, payload)
        for index, payload in enumerate(payloads, start=1)
    ]
