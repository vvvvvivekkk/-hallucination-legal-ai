from __future__ import annotations

from app.core.models import LegalMetadata, Page, ParsedDocument
from app.ingestion.chunker import SummaryAugmentedChunker
from app.ingestion.summarizer import LegalSummarizer


def _meta() -> LegalMetadata:
    return LegalMetadata(doc_id="doc-1", source_file="act.pdf", title="Act", year=1860, doc_type="statute")


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument(
        path="a.pdf",
        content_type="pdf",
        pages=[Page(1, text)],
        sha256="b" * 64,
    )


def test_chunk_word_budget() -> None:
    chunker = SummaryAugmentedChunker(
        chunk_size=100,
        chunk_overlap=20,
        min_chunk_words=10,
        enable_summary=False,
        embed_summary_augment=False,
    )
    text = "word " * 500
    chunks = chunker.chunk(_doc(text), _meta())
    assert chunks
    assert all(chunk.word_count <= 120 for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert len({chunk.chunk_id for chunk in chunks}) > 1


def test_min_chunk_words_filters() -> None:
    chunker = SummaryAugmentedChunker(
        chunk_size=200,
        chunk_overlap=0,
        min_chunk_words=50,
        enable_summary=False,
    )
    text = "short " * 30
    chunks = chunker.chunk(_doc(text), _meta())
    assert all(chunk.word_count >= 50 for chunk in chunks)


def test_summary_augmentation() -> None:
    chunker = SummaryAugmentedChunker(
        chunk_size=50,
        chunk_overlap=10,
        min_chunk_words=5,
        enable_summary=True,
        embed_summary_augment=True,
        summarizer=LegalSummarizer(),
    )
    text = "The court held that the accused is liable for the offence. " * 40
    chunks = chunker.chunk(_doc(text), _meta())
    assert chunks
    assert all(chunk.summary for chunk in chunks)
    assert all("[Summary]" in chunk.augmented_text for chunk in chunks)
    assert all(chunk.augmented_text.startswith(chunk.text) for chunk in chunks)


def test_summary_augment_disabled() -> None:
    chunker = SummaryAugmentedChunker(
        chunk_size=50,
        chunk_overlap=10,
        min_chunk_words=5,
        enable_summary=True,
        embed_summary_augment=False,
        summarizer=LegalSummarizer(),
    )
    text = "The accused was found guilty of murder. " * 40
    chunks = chunker.chunk(_doc(text), _meta())
    assert chunks
    assert all(chunk.augmented_text == chunk.text for chunk in chunks)
