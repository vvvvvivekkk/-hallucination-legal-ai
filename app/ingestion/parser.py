from __future__ import annotations

import html as html_module
import io
import re
import zipfile
from pathlib import Path
from typing import Any

from ..core.exceptions import ParsingError
from ..core.logger import get_logger
from ..core.models import Page, ParsedDocument, SourceFile
from ..core.utils import sha256_file

_TAG_RE = re.compile(r"<[^>]+>")
_DOCX_PARAGRAPH_RE = re.compile(r"</w:p>|<w:tab[^>]*/>")
_UNSUPPORTED_EXT = re.compile(r"^[A-Za-z0-9]+$")


class PDFParser:
    def __init__(
        self,
        enable_ocr: bool = True,
        ocr_min_chars: int = 10,
        ocr_dpi: int = 200,
        logger: object | None = None,
    ) -> None:
        self.enable_ocr = enable_ocr
        self.ocr_min_chars = ocr_min_chars
        self.ocr_dpi = ocr_dpi
        self._logger = logger or get_logger(self.__class__.__name__)
        self._tesseract: Any | None = None

    def _load_tesseract(self) -> None:
        if self._tesseract is not None:
            return
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            self._tesseract = pytesseract
        except Exception as exc:  # pragma: no cover - environment dependent
            self._tesseract = None
            self._logger.warning("pytesseract/tesseract unavailable, OCR fallback disabled: %s", exc)

    def _extract_with_ocr(self, page: Any) -> str:
        self._load_tesseract()
        if self._tesseract is None:
            return ""
        try:
            import fitz
            from PIL import Image

            matrix = fitz.Matrix(self.ocr_dpi / 72, self.ocr_dpi / 72)
            pix = page.get_pixmap(matrix=matrix)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            return self._tesseract.image_to_string(image)
        except Exception as exc:  # pragma: no cover - environment dependent
            self._logger.warning("OCR extraction failed: %s", exc)
            return ""

    def parse(self, path: str | Path) -> ParsedDocument:
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover
            raise ParsingError("PyMuPDF is required for PDF parsing", cause=exc)

        pdf_path = Path(path)
        try:
            document = fitz.open(str(pdf_path))
        except Exception as exc:
            raise ParsingError(f"Failed to open PDF: {pdf_path.name}", cause=exc)

        pages: list[Page] = []
        try:
            for index, page in enumerate(document, start=1):
                text = page.get_text("text") or ""
                if self.enable_ocr and len(text.strip()) < self.ocr_min_chars:
                    ocr_text = self._extract_with_ocr(page)
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                pages.append(Page(number=index, text=text))
        finally:
            document.close()

        return ParsedDocument(
            path=str(pdf_path),
            content_type="pdf",
            pages=pages,
            sha256=sha256_file(pdf_path),
        )


def _strip_html(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = _TAG_RE.sub(" ", text)
    text = html_module.unescape(text)
    return text


def _extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ParsingError(f"Invalid DOCX file: {path.name}", cause=exc)
    xml = _DOCX_PARAGRAPH_RE.sub("\n", xml)
    xml = _TAG_RE.sub("", xml)
    return html_module.unescape(xml)


class TextParser:
    def parse(self, path: str | Path) -> ParsedDocument:
        text_path = Path(path)
        extension = text_path.suffix.lower()
        if extension in {".txt", ".md"}:
            text = text_path.read_text(encoding="utf-8", errors="replace")
        elif extension in {".html", ".htm"}:
            text = _strip_html(text_path.read_text(encoding="utf-8", errors="replace"))
        elif extension == ".docx":
            text = _extract_docx_text(text_path)
        else:
            raise ParsingError(f"Unsupported file type: {extension}")
        return ParsedDocument(
            path=str(text_path),
            content_type=extension.lstrip("."),
            pages=[Page(number=1, text=text)],
            sha256=sha256_file(text_path),
        )


def parse_source(
    source: SourceFile,
    pdf_parser: PDFParser | None = None,
    text_parser: TextParser | None = None,
) -> ParsedDocument:
    if source.extension == ".pdf":
        return (pdf_parser or PDFParser()).parse(source.path)
    return (text_parser or TextParser()).parse(source.path)
