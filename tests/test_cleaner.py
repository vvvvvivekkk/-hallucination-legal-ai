from __future__ import annotations

from app.core.models import Page
from app.ingestion.cleaner import TextCleaner


def test_unicode_normalization() -> None:
    cleaner = TextCleaner()
    assert cleaner.normalize_text("Caf\u00e9 \u00a0\u00a0 text \x0c") == "Café text"


def test_whitespace_collapse() -> None:
    cleaner = TextCleaner()
    assert cleaner.clean_text("a\n\n\n  b   c") == "a\nb c"


def test_page_number_removal() -> None:
    cleaner = TextCleaner()
    assert cleaner.clean_text("Page 3\nBody text") == "Body text"
    assert cleaner.clean_text("42\nBody") == "Body"
    assert cleaner.clean_text("p. 12\nBody") == "Body"


def test_header_footer_removal_across_pages() -> None:
    cleaner = TextCleaner()
    header = "Government of India Official Document"
    pages = [
        Page(1, f"{header}\nPage 1\nThe first paragraph of the act."),
        Page(2, f"{header}\nThe second paragraph continues here."),
    ]
    cleaned = cleaner.clean_pages(pages)
    assert all(header not in page.text for page in cleaned)
    assert "first paragraph" in cleaned[0].text
    assert "second paragraph" in cleaned[1].text


def test_single_page_keeps_body() -> None:
    cleaner = TextCleaner()
    cleaned = cleaner.clean_text("Some body content\n12\nmore content")
    assert "Some body content" in cleaned
    assert "more content" in cleaned
