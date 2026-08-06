from __future__ import annotations

import re
import unicodedata

from ..core.logger import get_logger
from ..core.models import Page, ParsedDocument

_PAGE_NUMBER_RE = re.compile(r"^\s*(?:p(?:age)?\.?\s*)?\d{1,5}\s*$", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


class TextCleaner:
    def __init__(
        self,
        remove_headers_footers: bool = True,
        remove_page_numbers: bool = True,
        logger: object | None = None,
    ) -> None:
        self.remove_headers_footers = remove_headers_footers
        self.remove_page_numbers = remove_page_numbers
        self._logger = logger or get_logger(self.__class__.__name__)

    def normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\x00", "").replace("\x0c", "")
        text = text.replace("\xa0", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = _WHITESPACE_RE.sub(" ", text)
        text = _MULTI_BLANK_RE.sub("\n\n", text)
        text = text.replace("\u2022", "- ").replace("\u25cf", "- ")
        return text.strip()

    def _is_page_number(self, line: str) -> bool:
        return bool(_PAGE_NUMBER_RE.match(line))

    def detect_repeated_lines(self, pages: list[Page]) -> set[str]:
        counts: dict[str, int] = {}
        for page in pages:
            seen: set[str] = set()
            for raw in page.text.splitlines():
                normalized = self.normalize_text(raw)
                if not normalized or self._is_page_number(normalized):
                    continue
                if normalized not in seen:
                    seen.add(normalized)
                    counts[normalized] = counts.get(normalized, 0) + 1
        threshold = max(2, int(len(pages) * 0.5) + 1)
        return {line for line, count in counts.items() if count >= threshold}

    def clean_text(self, text: str, repeated_lines: set[str] | None = None) -> str:
        lines: list[str] = []
        for raw in text.splitlines():
            line = self.normalize_text(raw)
            if self.remove_page_numbers and self._is_page_number(line):
                continue
            if repeated_lines and line in repeated_lines:
                continue
            if line:
                lines.append(line)
        return self.normalize_text("\n".join(lines))

    def clean_pages(self, pages: list[Page]) -> list[Page]:
        repeated: set[str] = set()
        if self.remove_headers_footers and len(pages) > 1:
            repeated = self.detect_repeated_lines(pages)
        return [Page(number=page.number, text=self.clean_text(page.text, repeated)) for page in pages]

    def clean_document(self, document: ParsedDocument) -> ParsedDocument:
        return ParsedDocument(
            path=document.path,
            content_type=document.content_type,
            pages=self.clean_pages(document.pages),
            sha256=document.sha256,
        )
