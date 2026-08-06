from __future__ import annotations

from app.core.models import Page, ParsedDocument
from app.ingestion.metadata import extract_metadata, extract_sections


def _doc(text: str, filename: str = "document.pdf") -> ParsedDocument:
    return ParsedDocument(
        path=filename,
        content_type="pdf",
        pages=[Page(1, text)],
        sha256="a" * 64,
    )


def test_year_from_filename() -> None:
    doc = _doc("Some body text without a year", filename="Indian_Penal_Code_1860.pdf")
    metadata = extract_metadata(doc)
    assert metadata.year == 1860


def test_year_from_content() -> None:
    doc = _doc("This code was enacted in the year 1950.")
    metadata = extract_metadata(doc)
    assert metadata.year == 1950


def test_doc_type_case() -> None:
    metadata = extract_metadata(_doc("The appellant X v. Y claimed damages."))
    assert metadata.doc_type == "case"


def test_doc_type_statute() -> None:
    metadata = extract_metadata(_doc("The Indian Penal Code, 1860. Section 300 defines murder."))
    assert metadata.doc_type == "statute"


def test_sections_detected() -> None:
    text = (
        "Section 300 - Murder\nDefinition of murder.\n"
        "Section 302 - Punishment\nPunishment for murder."
    )
    metadata = extract_metadata(_doc(text))
    numbers = [section.number for section in metadata.sections if section.number]
    assert "300" in numbers
    assert "302" in numbers


def test_court_detection() -> None:
    metadata = extract_metadata(_doc("The Supreme Court of India held that the appeal fails."))
    assert metadata.court == "Supreme Court"


def test_jurisdiction_detection() -> None:
    metadata = extract_metadata(_doc("The Indian Penal Code applies across India."))
    assert metadata.jurisdiction == "India"


def test_extract_sections_fallback() -> None:
    sections = extract_sections(_doc("No headings here, just plain body text about contracts."))
    assert len(sections) == 1
    assert sections[0].number is None
