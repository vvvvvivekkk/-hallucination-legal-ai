from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z0-9']+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")

_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "while",
        "is", "are", "was", "were", "be", "been", "being", "am", "do", "does", "did",
        "have", "has", "had", "having", "will", "would", "shall", "should", "may",
        "might", "must", "can", "could", "of", "to", "for", "with", "by", "from", "in",
        "on", "at", "as", "into", "upon", "over", "under", "about", "than", "that",
        "this", "these", "those", "it", "its", "he", "she", "they", "them", "we", "us",
        "you", "your", "my", "mine", "his", "her", "their", "ours", "yours", "i",
        "not", "no", "nor", "such", "which", "who", "whom", "whose", "what", "where",
        "why", "how", "also", "only", "just", "very", "there", "here", "each", "both",
        "some", "any", "all", "many", "much", "more", "most", "other", "another",
        "per", "via", "etc", "e", "g", "eg", "ie",
    }
)


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def significant_tokens(text: str) -> list[str]:
    return [
        token
        for token in tokenize(text)
        if token not in _STOPWORDS and len(token) > 1 and not token.isdigit()
    ]


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]


def overlap(left_tokens: list[str], right_tokens: list[str]) -> float:
    if not left_tokens or not right_tokens:
        return 0.0
    left = set(left_tokens)
    right = set(right_tokens)
    return round(2.0 * len(left & right) / (len(left) + len(right)), 4)


def containment(inner_tokens: list[str], outer_tokens: list[str]) -> float:
    if not inner_tokens:
        return 0.0
    outer = set(outer_tokens)
    matched = sum(1 for token in inner_tokens if token in outer)
    return round(matched / len(inner_tokens), 4)


def best_containment(inner_tokens: list[str], outer_tokens_list: list[list[str]]) -> float:
    if not inner_tokens or not outer_tokens_list:
        return 0.0
    return max(containment(inner_tokens, outer) for outer in outer_tokens_list)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return round(min(high, max(low, value)), 4)


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
