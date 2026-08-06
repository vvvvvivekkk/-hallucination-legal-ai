from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_CHUNK_INTERNAL = {"chunk_id", "doc_id", "chunk_text", "embedded_text", "summary"}


@dataclass
class SourceFile:
    path: str
    filename: str
    extension: str
    size: int
    sha256: str


@dataclass
class Page:
    number: int
    text: str


@dataclass
class ParsedDocument:
    path: str
    content_type: str
    pages: list[Page]
    sha256: str

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


@dataclass
class Section:
    header: str | None
    number: str | None
    text: str
    page: int


@dataclass
class LegalMetadata:
    doc_id: str
    source_file: str
    title: str
    year: int | None = None
    court: str | None = None
    jurisdiction: str | None = None
    doc_type: str = "general"
    page_count: int = 0
    sections: list[Section] = field(default_factory=list)
    ingested_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "doc_title": self.title,
            "year": self.year,
            "court": self.court,
            "jurisdiction": self.jurisdiction,
            "doc_type": self.doc_type,
            "page_count": self.page_count,
        }
        if self.ingested_at is not None:
            payload["ingested_at"] = self.ingested_at
        payload.update(self.extra)
        return payload


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    augmented_text: str
    summary: str | None = None
    section: str | None = None
    section_number: str | None = None
    page: int = 0
    seq: int = 0
    word_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            **self.metadata,
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "chunk_text": self.text,
            "embedded_text": self.augmented_text,
            "summary": self.summary,
            "section": self.section,
            "section_number": self.section_number,
            "page": self.page,
            "chunk_seq": self.seq,
            "word_count": self.word_count,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Chunk":
        text = payload.get("chunk_text", "")
        return cls(
            chunk_id=payload["chunk_id"],
            doc_id=payload.get("doc_id", ""),
            text=text,
            augmented_text=payload.get("embedded_text", text),
            summary=payload.get("summary"),
            section=payload.get("section"),
            section_number=payload.get("section_number"),
            page=payload.get("page", 0),
            seq=payload.get("chunk_seq", 0),
            word_count=payload.get("word_count", 0),
            metadata={k: v for k, v in payload.items() if k not in _CHUNK_INTERNAL},
        )
