from __future__ import annotations

import re
from collections import Counter
from math import log
from typing import Callable

from ..core.logger import get_logger

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n")


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text)]
    return [part for part in parts if part]


def extractive_summary(text: str, max_sentences: int = 3, ratio: float = 0.25) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= 100:
        return cleaned
    sentences = split_sentences(cleaned)
    if len(sentences) <= max_sentences:
        return cleaned

    words = re.findall(r"\w+", cleaned.lower())
    total = max(len(words), 1)
    frequencies = Counter(words)
    idf = {word: log(1 + total / (count + 1)) for word, count in frequencies.items()}

    scored: list[tuple[int, str, float]] = []
    for index, sentence in enumerate(sentences):
        tokens = re.findall(r"\w+", sentence.lower())
        if not tokens:
            continue
        score = sum(idf.get(token, 0.0) for token in tokens) / (len(tokens) ** 0.5)
        scored.append((index, sentence, score))

    scored.sort(key=lambda item: item[2], reverse=True)
    top = scored[:max_sentences]
    top.sort(key=lambda item: item[0])
    return " ".join(sentence for _, sentence, _ in top)


class LegalSummarizer:
    def __init__(
        self,
        max_sentences: int = 3,
        llm: Callable[[str], str] | None = None,
        logger: object | None = None,
    ) -> None:
        self._max_sentences = max_sentences
        self._llm = llm
        self._logger = logger or get_logger(self.__class__.__name__)

    def summarize(self, text: str, header: str | None = None) -> str:
        if self._llm is not None:
            try:
                result = (self._llm(text) or "").strip()
                if result:
                    return result
            except Exception as exc:
                self._logger.warning("LLM summarization failed, falling back to extractive: %s", exc)
        return extractive_summary(text, max_sentences=self._max_sentences)
