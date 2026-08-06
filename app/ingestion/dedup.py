from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

from ..core.logger import get_logger

_MAX_SHINGLES = 2000


class DuplicateDetector:
    def __init__(
        self,
        store_path: str | Path,
        threshold: float = 0.85,
        num_hashes: int = 4,
        shingle_size: int = 64,
        logger: object | None = None,
    ) -> None:
        self._path = Path(store_path)
        self._threshold = threshold
        self._num_hashes = num_hashes
        self._shingle_size = shingle_size
        self._logger = logger or get_logger(self.__class__.__name__)
        self._exact: dict[str, str] = {}
        self._signatures: dict[str, list[int]] = {}
        self._bands: dict[tuple[int, int], list[str]] = {}
        self._lock = threading.RLock()
        self.load()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9]+", text.lower())

    def content_sha(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _signature(self, tokens: list[str]) -> list[int]:
        size = min(self._shingle_size, max(2, len(tokens) // 4))
        shingles: set[str] = set()
        for i in range(0, len(tokens) - size + 1):
            shingles.add(" ".join(tokens[i : i + size]))
        if not shingles:
            shingles = {"__empty__"}
        if len(shingles) > _MAX_SHINGLES:
            shingles = set(sorted(shingles)[:_MAX_SHINGLES])
        signature: list[int] = []
        for seed in range(self._num_hashes):
            minimum: int | None = None
            for shingle in shingles:
                digest = hashlib.md5(f"{seed}:{shingle}".encode("utf-8")).hexdigest()
                value = int(digest[:8], 16)
                minimum = value if minimum is None else min(minimum, value)
            signature.append(minimum if minimum is not None else 0)
        return signature

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            self._logger.warning("Failed to load dedup store %s: %s", self._path, exc)
            return
        self._exact = data.get("exact", {})
        self._signatures = {k: list(v) for k, v in data.get("signatures", {}).items()}
        self._rebuild_bands()

    def _rebuild_bands(self) -> None:
        bands: dict[tuple[int, int], list[str]] = {}
        for doc_id, signature in self._signatures.items():
            for index, value in enumerate(signature):
                bands.setdefault((index, value), []).append(doc_id)
        self._bands = bands

    def save(self) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"exact": self._exact, "signatures": self._signatures}
            temp = self._path.with_suffix(".tmp")
            temp.write_text(json.dumps(payload), encoding="utf-8")
            temp.replace(self._path)

    def add(self, text: str, doc_id: str) -> None:
        tokens = self._tokens(text)
        with self._lock:
            self._exact[self.content_sha(text)] = doc_id
            signature = self._signature(tokens)
            self._signatures[doc_id] = signature
            for index, value in enumerate(signature):
                self._bands.setdefault((index, value), []).append(doc_id)

    def is_duplicate(self, text: str) -> tuple[bool, str | None]:
        exact_sha = self.content_sha(text)
        with self._lock:
            if exact_sha in self._exact:
                return True, self._exact[exact_sha]
            signature = self._signature(self._tokens(text))
            candidates: set[str] = set()
            for index, value in enumerate(signature):
                candidates.update(self._bands.get((index, value), []))
            best_id: str | None = None
            best_similarity = 0.0
            for candidate in candidates:
                other = self._signatures.get(candidate)
                if other is None:
                    continue
                matches = sum(1 for a, b in zip(signature, other) if a == b)
                similarity = matches / self._num_hashes
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_id = candidate
            if best_id is not None and best_similarity >= self._threshold:
                return True, best_id
            return False, None
