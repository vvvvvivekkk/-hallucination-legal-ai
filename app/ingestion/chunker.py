from __future__ import annotations

from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core.logger import get_logger
from ..core.models import Chunk, LegalMetadata, ParsedDocument, Section
from .metadata import extract_sections
from .summarizer import LegalSummarizer


def _word_count(text: str) -> int:
    return len(text.split())


class SummaryAugmentedChunker:
    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        min_chunk_words: int = 20,
        enable_summary: bool = True,
        embed_summary_augment: bool = True,
        summarizer: LegalSummarizer | None = None,
        logger: object | None = None,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_chunk_words = min_chunk_words
        self._enable_summary = enable_summary
        self._embed_summary_augment = embed_summary_augment
        self._summarizer = summarizer or LegalSummarizer()
        self._logger = logger or get_logger(self.__class__.__name__)

    def _splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            length_function=_word_count,
            keep_separator=False,
        )

    def chunk(self, document: ParsedDocument, metadata: LegalMetadata) -> list[Chunk]:
        sections = metadata.sections or extract_sections(document)
        if not sections:
            sections = [Section(header=None, number=None, text=document.text, page=1)]

        splitter = self._splitter()
        chunks: list[Chunk] = []
        seq = 0
        metadata_payload = metadata.to_payload()

        for section in sections:
            text = section.text.strip()
            if not text:
                continue
            summary: str | None = None
            if self._enable_summary:
                summary = self._summarizer.summarize(text, section.header) or None
            for piece in splitter.split_text(text):
                words = piece.split()
                if len(words) < self._min_chunk_words:
                    continue
                augmented = piece
                if summary and self._embed_summary_augment:
                    augmented = f"{piece}\n[Summary] {summary}"
                chunk = Chunk(
                    chunk_id=f"{metadata.doc_id}:{seq:05d}",
                    doc_id=metadata.doc_id,
                    text=piece,
                    augmented_text=augmented,
                    summary=summary,
                    section=section.header,
                    section_number=section.number,
                    page=section.page,
                    seq=seq,
                    word_count=len(words),
                    metadata=metadata_payload,
                )
                chunks.append(chunk)
                seq += 1

        if not chunks:
            self._logger.warning("No chunks produced for document %s", metadata.doc_id)
        return chunks
