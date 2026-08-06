from __future__ import annotations

import re
from pathlib import Path

from ..core.models import LegalMetadata, ParsedDocument, Section

_YEAR_RE = re.compile(r"(18|19|20)\d{2}")
_TITLE_WORD_RE = re.compile(r"[A-Za-z0-9]")

_COURTS = [
    "Supreme Court",
    "High Court",
    "Session Court",
    "District Court",
    "Federal Court",
    "Court of Appeal",
    "Court of Appeals",
    "Constitutional Court",
    "Tribunal",
]

_JURISDICTIONS = {
    "india": "India",
    "indian": "India",
    "united states": "United States",
    "usa": "United States",
    "u.s.a": "United States",
    "united kingdom": "United Kingdom",
    "u.k.": "United Kingdom",
    "england": "United Kingdom",
    "european union": "European Union",
    "eu": "European Union",
    "australia": "Australia",
    "canada": "Canada",
    "south africa": "South Africa",
    "singapore": "Singapore",
}

_STATUTE_KEYWORDS = (
    "ACT", "CODE", "ORDER", "RULE", "REGULATION", "CONSTITUTION", "AMENDMENT",
    "SCHEDULE", "STATUTE",
)

_SECTION_HEADER_PATTERNS = [
    re.compile(r"^\s*Section\s+([0-9][A-Z0-9.\-]*)", re.IGNORECASE),
    re.compile(r"^\s*Article\s+([0-9][A-Z0-9.\-]*)", re.IGNORECASE),
    re.compile(r"^\s*Rule\s+([0-9][A-Z0-9.\-]*)", re.IGNORECASE),
    re.compile(r"^\s*(?:CHAPTER|PART|TITLE|SCHEDULE|ANNEXURE)\s+([0-9IVX]+)", re.IGNORECASE),
    re.compile(r"^\s*(?:§|Sec(?:tion)?\.?)\s*[:.\- ]*\s*([0-9][A-Z0-9.\-]*)", re.IGNORECASE),
]

_GENERIC_HEADER_RE = re.compile(r"^[A-Z][A-Za-z0-9 &'()/:,\-]{3,80}$")
_TERMINAL_PUNCT_RE = re.compile(r"[.!?:;]$")


def _match_header(line: str) -> tuple[str, str | None] | None:
    for pattern in _SECTION_HEADER_PATTERNS:
        match = pattern.match(line)
        if match:
            return line, match.group(1)
    if (
        len(line) <= 80
        and _GENERIC_HEADER_RE.match(line)
        and not _TERMINAL_PUNCT_RE.search(line)
        and " v. " not in line
    ):
        return line, None
    return None


def extract_sections(document: ParsedDocument) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    buffer: list[str] = []

    for page in document.pages:
        for raw in page.text.splitlines():
            line = raw.strip()
            if not line:
                continue
            match = _match_header(line)
            if match is not None:
                if current is not None:
                    current.text = "\n".join(buffer).strip()
                    if current.text:
                        sections.append(current)
                header, number = match
                current = Section(header=header, number=number, text="", page=page.number)
                buffer = []
            elif current is not None:
                buffer.append(line)

    if current is not None:
        current.text = "\n".join(buffer).strip()
        if current.text:
            sections.append(current)

    if not sections:
        sections.append(Section(header=None, number=None, text=document.text, page=1))
    return sections


def _find_year(*texts: str) -> int | None:
    for text in texts:
        match = _YEAR_RE.search(text)
        if match:
            return int(match.group(0))
    return None


def _slugify(filename: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", filename.lower()).strip("-")
    return slug[:40] or "document"


def _infer_title(filename_stem: str, text: str) -> str:
    if _TITLE_WORD_RE.search(filename_stem) and len(filename_stem) >= 4:
        return filename_stem.replace("_", " ").replace("-", " ").strip()
    for raw in text.splitlines()[:10]:
        line = raw.strip()
        if line and not _TERMINAL_PUNCT_RE.search(line) and len(line) <= 120:
            return line
    return text[:80].strip()


def _infer_doc_type(text: str) -> str:
    if re.search(r"\bv\.\s|\bvs\.?\s", text, re.IGNORECASE):
        return "case"
    upper = text.upper()
    if any(keyword in upper for keyword in _STATUTE_KEYWORDS):
        return "statute"
    return "general"


def _infer_court(text: str) -> str | None:
    for court in _COURTS:
        if re.search(rf"\b{re.escape(court)}\b", text, re.IGNORECASE):
            return court
    return None


def _infer_jurisdiction(text: str) -> str | None:
    lowered = text.lower()
    for keyword, jurisdiction in _JURISDICTIONS.items():
        if keyword in lowered:
            return jurisdiction
    return None


def extract_metadata(document: ParsedDocument) -> LegalMetadata:
    path = Path(document.path)
    filename = path.name
    filename_stem = path.stem
    text_head = document.text[:4000]

    doc_id = f"{document.sha256[:12]}-{_slugify(filename_stem)}"
    return LegalMetadata(
        doc_id=doc_id,
        source_file=filename,
        title=_infer_title(filename_stem, document.text),
        year=_find_year(filename, text_head),
        court=_infer_court(text_head),
        jurisdiction=_infer_jurisdiction(f"{filename} {text_head}"),
        doc_type=_infer_doc_type(text_head),
        page_count=document.page_count,
        sections=extract_sections(document),
    )
