from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np


@dataclass
class RankedResult:
    chunk_id: str
    score: float
    payload: dict[str, Any]
    dense_score: float | None = None
    lexical_score: float | None = None
    rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "score": self.score,
            "payload": self.payload,
            "dense_score": self.dense_score,
            "lexical_score": self.lexical_score,
            "rank": self.rank,
        }


class DenseSearcher(Protocol):
    def semantic_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        conditions: dict[str, Any] | None = None,
    ) -> list[RankedResult]: ...


class LexicalSearcher(Protocol):
    def search(
        self,
        query: str,
        top_k: int = 10,
        conditions: dict[str, Any] | None = None,
    ) -> list[RankedResult]: ...
