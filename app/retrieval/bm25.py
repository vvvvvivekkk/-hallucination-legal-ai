from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Iterable

import numpy as np
from rank_bm25 import BM25Okapi

from ..core.logger import get_logger
from .base import RankedResult
from .filters import match_filters

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u00a7][A-Za-z0-9'\u00a7.\-]*")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class LocalBm25Index:
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        store_path: str | Path | None = None,
        logger: object | None = None,
    ) -> None:
        self._k1 = k1
        self._b = b
        self._store_path = Path(store_path) if store_path else None
        self._logger = logger or get_logger(self.__class__.__name__)
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._tokenized: list[list[str]] = []
        self._payloads: dict[str, dict] = {}

    @property
    def ready(self) -> bool:
        return self._bm25 is not None

    def build(self, entries: Iterable[tuple[str, str, dict]]) -> None:
        ids: list[str] = []
        tokenized: list[list[str]] = []
        payloads: dict[str, dict] = {}
        for chunk_id, text, payload in entries:
            if not text or not text.strip():
                continue
            ids.append(chunk_id)
            tokenized.append(tokenize(text))
            payloads[chunk_id] = payload
        self._ids = ids
        self._tokenized = tokenized
        self._payloads = payloads
        if tokenized:
            self._bm25 = BM25Okapi(tokenized, k1=self._k1, b=self._b)
        else:
            self._bm25 = None
        self._logger.info("Built local BM25 index with %d documents", len(ids))

    def add_chunks(self, chunks: Iterable[tuple[str, str, dict]]) -> None:
        entries = [(chunk_id, text, payload) for chunk_id, text, payload in chunks]
        existing = list(zip(self._ids, self._tokenized, [self._payloads[i] for i in self._ids]))
        self.build([*existing, *entries])

    def search(
        self,
        query: str,
        top_k: int = 10,
        conditions: dict | None = None,
    ) -> list[RankedResult]:
        if not self.ready:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores = np.asarray(self._bm25.get_scores(query_tokens), dtype=float)
        allowed = [
            index
            for index, chunk_id in enumerate(self._ids)
            if match_filters(self._payloads[chunk_id], conditions)
        ]
        if not allowed:
            return []
        order = np.argsort(-scores[allowed])[:top_k]
        results: list[RankedResult] = []
        for position in order:
            index = allowed[position]
            chunk_id = self._ids[index]
            results.append(
                RankedResult(
                    chunk_id=chunk_id,
                    score=float(scores[index]),
                    payload=self._payloads[chunk_id],
                    lexical_score=float(scores[index]),
                )
            )
        return results

    def save(self, path: str | Path | None = None) -> None:
        target = Path(path) if path else self._store_path
        if target is None:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ids": self._ids,
            "tokenized": self._tokenized,
            "payloads": self._payloads,
            "k1": self._k1,
            "b": self._b,
        }
        with target.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, path: str | Path | None = None) -> bool:
        target = Path(path) if path else self._store_path
        if target is None or not target.exists():
            return False
        with target.open("rb") as handle:
            payload = pickle.load(handle)
        self._ids = payload["ids"]
        self._tokenized = payload["tokenized"]
        self._payloads = payload["payloads"]
        self._k1 = payload["k1"]
        self._b = payload["b"]
        self._bm25 = BM25Okapi(self._tokenized, k1=self._k1, b=self._b)
        self._logger.info("Loaded local BM25 index with %d documents", len(self._ids))
        return True
