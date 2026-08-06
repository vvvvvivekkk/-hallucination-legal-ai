from __future__ import annotations

import fitz

from app.core.models import SourceFile
from app.ingestion.parser import PDFParser, TextParser, parse_source


def _make_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "The Indian Penal Code, 1860\nSection 300 defines murder.")
    document.save(str(path))
    document.close()
    return path


def test_pdf_parser_extracts_text(tmp_path) -> None:
    path = _make_pdf(tmp_path)
    parser = PDFParser(enable_ocr=False)
    parsed = parser.parse(path)
    assert parsed.page_count == 1
    assert parsed.content_type == "pdf"
    assert "Section 300" in parsed.text
    assert len(parsed.sha256) == 64


def test_text_parser_txt(tmp_path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("Some legal note about section 302.")
    parsed = TextParser().parse(path)
    assert "section 302" in parsed.text.lower()
    assert parsed.content_type == "txt"


def test_parse_source_dispatch(tmp_path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    source = SourceFile(
        path=str(pdf), filename=pdf.name, extension=".pdf", size=pdf.stat().st_size, sha256="x"
    )
    text = tmp_path / "doc.md"
    text.write_text("# Heading\nBody")
    text_source = SourceFile(
        path=str(text), filename=text.name, extension=".md", size=text.stat().st_size, sha256="y"
    )
    parsed = parse_source(text_source)
    assert parsed.content_type == "md"
