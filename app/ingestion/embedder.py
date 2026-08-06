from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Any

import numpy as np

from ..core.exceptions import EmbeddingError
from ..core.logger import get_logger
from ..core.models import Chunk

DEFAULT_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingCache:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self._path), check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "model TEXT NOT NULL, key TEXT NOT NULL, dim INTEGER NOT NULL, "
            "vector BLOB NOT NULL, PRIMARY KEY (model, key))"
        )
        self._connection.commit()
        self._lock = threading.Lock()

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, model: str, text: str) -> np.ndarray | None:
        row = None
        with self._lock:
            row = self._connection.execute(
                "SELECT dim, vector FROM embeddings WHERE model=? AND key=?",
                (model, self._key(text)),
            ).fetchone()
        if row is None:
            return None
        dim, blob = row
        return np.frombuffer(blob, dtype=np.float32).reshape((dim,))

    def set(self, model: str, text: str, vector: np.ndarray) -> None:
        blob = np.asarray(vector, dtype=np.float32).tobytes()
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO embeddings (model, key, dim, vector) VALUES (?,?,?,?)",
                (model, self._key(text), int(np.asarray(vector).shape[0]), blob),
            )
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _auto_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


class Embedder:
    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        device: str | None = None,
        batch_size: int = 32,
        cache: EmbeddingCache | None = None,
        query_prefix: str | None = DEFAULT_QUERY_PREFIX,
        logger: object | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._cache = cache
        self._query_prefix = query_prefix
        self._logger = logger or get_logger(self.__class__.__name__)
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                device = self._device or _auto_device()
                self._model = SentenceTransformer(self._model_name, device=device)
            except Exception as exc:
                raise EmbeddingError(
                    f"Failed to load embedding model {self._model_name}", cause=exc
                )
        return self._model

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        model = self._load()
        vectors = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)

    def dimension(self) -> int:
        model = self._load()
        return int(model.get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension()), dtype=np.float32)
        results: list[np.ndarray | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []
        for index, text in enumerate(texts):
            cached = self._cache.get(self._model_name, text) if self._cache else None
            if cached is not None:
                results[index] = cached
            else:
                missing_indices.append(index)
                missing_texts.append(text)
        if missing_texts:
            vectors = self._encode_batch(missing_texts)
            for position, vector in zip(missing_indices, vectors):
                if self._cache is not None:
                    self._cache.set(self._model_name, texts[position], vector)
                results[position] = np.asarray(vector, dtype=np.float32)
        return np.stack(results)

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]

    def embed_query(self, text: str) -> np.ndarray:
        prefixed = f"{self._query_prefix}{text}" if self._query_prefix else text
        return self.embed_texts([prefixed])[0]

    def embed_chunks(self, chunks: list[Chunk], use_augmented: bool = True) -> np.ndarray:
        texts = [chunk.augmented_text if use_augmented else chunk.text for chunk in chunks]
        return self.embed_texts(texts)
