from __future__ import annotations

import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..core.exceptions import (
    CollectionNotFoundError,
    QdrantUnavailableError,
)
from ..core.logger import get_logger
from ..core.models import Chunk
from .base import RankedResult

KEYWORD_FIELDS = (
    "doc_id", "source_file", "doc_title", "court", "jurisdiction",
    "doc_type", "section", "section_number",
)
INTEGER_FIELDS = ("year", "page", "chunk_seq", "page_count")
FULLTEXT_FIELD = "chunk_text"

_NAMESPACE = uuid.NAMESPACE_URL


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"legal-ai-rag/{chunk_id}"))


def _build_filter(conditions: dict[str, Any] | None) -> models.Filter | None:
    if not conditions:
        return None
    must: list[models.FieldCondition] = []
    for field, spec in conditions.items():
        if isinstance(spec, dict):
            bounds = {key: value for key, value in spec.items() if key in {"min", "max"}}
            if bounds:
                must.append(models.FieldCondition(key=field, range=models.Range(**bounds)))
        elif isinstance(spec, (list, tuple, set)):
            must.append(
                models.FieldCondition(key=field, match=models.MatchAny(any=list(spec)))
            )
        else:
            must.append(models.FieldCondition(key=field, match=models.MatchValue(value=spec)))
    return models.Filter(must=must) if must else None


class QdrantStore:
    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        collection: str = "legal_corpus",
        embedding_dim: int = 768,
        timeout: int = 30,
        prefer_grpc: bool = False,
        max_retries: int = 3,
        logger: object | None = None,
    ) -> None:
        self._collection = collection
        self._embedding_dim = embedding_dim
        self._max_retries = max_retries
        self._logger = logger or get_logger(self.__class__.__name__)
        try:
            self._client = QdrantClient(
                url=url,
                api_key=api_key,
                timeout=timeout,
                prefer_grpc=prefer_grpc,
            )
        except Exception as exc:
            raise QdrantUnavailableError(f"Failed to create Qdrant client for {url}", cause=exc)

    def _retry(self, operation: str) -> Any:
        return retry(
            retry=retry_if_exception_type(QdrantUnavailableError),
            stop=stop_after_attempt(max(1, self._max_retries)),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            reraise=True,
        )(operation)

    def _call(self, function: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except QdrantUnavailableError:
            raise
        except (UnexpectedResponse, ConnectionError, OSError) as exc:
            raise QdrantUnavailableError(
                f"Qdrant operation failed: {exc.__class__.__name__}: {exc}", cause=exc
            )

    def ping(self) -> bool:
        try:
            self._call(self._client.get_collections)
            return True
        except QdrantUnavailableError:
            return False

    def collection_exists(self, collection: str | None = None) -> bool:
        name = collection or self._collection
        return self._retry(lambda: self._call(self._client.collection_exists, name))()

    def ensure_collection(self, collection: str | None = None) -> bool:
        name = collection or self._collection
        if self.collection_exists(name):
            return False
        self._retry(self._create_collection)(name)
        return True

    def _create_collection(self, name: str) -> None:
        self._call(
            self._client.create_collection,
            collection_name=name,
            vectors_config=models.VectorParams(
                size=self._embedding_dim,
                distance=models.Distance.COSINE,
                on_disk=True,
            ),
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=128, full_scan_threshold=10000),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=20000, memmap_threshold=20000
            ),
        )
        self._create_indexes(name)

    def _create_indexes(self, name: str) -> None:
        for field in KEYWORD_FIELDS:
            self._call(
                self._client.create_payload_index,
                collection_name=name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        for field in INTEGER_FIELDS:
            self._call(
                self._client.create_payload_index,
                collection_name=name,
                field_name=field,
                field_schema=models.PayloadSchemaType.INTEGER,
            )
        self._call(
            self._client.create_payload_index,
            collection_name=name,
            field_name=FULLTEXT_FIELD,
            field_schema=models.TextIndexParams(
                type=models.TextIndexType.TEXT,
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=25,
                lowercase=True,
            ),
        )

    def delete_collection(self, collection: str | None = None) -> None:
        name = collection or self._collection
        if self.collection_exists(name):
            self._call(self._client.delete_collection, collection_name=name)

    def recreate_collection(self, collection: str | None = None) -> None:
        name = collection or self._collection
        self.delete_collection(name)
        self.ensure_collection(name)

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[np.ndarray],
        payloads: list[dict[str, Any]],
        batch_size: int = 256,
    ) -> None:
        total = len(ids)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            self._call(
                self._client.upsert,
                collection_name=collection,
                points=models.Batch(
                    ids=ids[start:end],
                    vectors=[vector.tolist() for vector in vectors[start:end]],
                    payloads=payloads[start:end],
                ),
            )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        collection: str | None = None,
        embeddings: np.ndarray | None = None,
        batch_size: int = 256,
    ) -> None:
        name = collection or self._collection
        if not self.collection_exists(name):
            raise CollectionNotFoundError(f"Collection does not exist: {name}")
        if embeddings is None:
            raise ValueError("embeddings are required for upsert_chunks")
        if embeddings.shape[0] != len(chunks):
            raise ValueError("embedding count does not match chunk count")
        ids = [_point_id(chunk.chunk_id) for chunk in chunks]
        vectors = [np.asarray(embeddings[index], dtype=np.float32) for index in range(len(chunks))]
        payloads = [chunk.payload() for chunk in chunks]
        self.upsert(name, ids, vectors, payloads, batch_size=batch_size)

    def set_payload(self, collection: str, point_ids: list[str], payload: dict[str, Any]) -> None:
        self._call(self._client.set_payload, collection_name=collection, payload=payload, points=point_ids)

    def update_chunk_metadata(
        self, collection: str, chunk_ids: list[str], payload: dict[str, Any]
    ) -> None:
        self.set_payload(collection, [_point_id(chunk_id) for chunk_id in chunk_ids], payload)

    def delete_points(self, collection: str, point_ids: list[str]) -> None:
        self._call(self._client.delete, collection_name=collection, points_selector=point_ids)

    def delete_chunks(self, collection: str, chunk_ids: list[str]) -> None:
        self.delete_points(collection, [_point_id(chunk_id) for chunk_id in chunk_ids])

    def delete_by_conditions(self, collection: str, conditions: dict[str, Any] | None) -> None:
        query_filter = _build_filter(conditions)
        if query_filter is not None:
            self._call(
                self._client.delete,
                collection_name=collection,
                points_selector=models.FilterSelector(filter=query_filter),
            )

    def delete_by_doc(self, collection: str, doc_id: str) -> None:
        self.delete_by_conditions(collection, {"doc_id": doc_id})

    def count(self, collection: str | None = None) -> int:
        name = collection or self._collection
        result = self._call(self._client.count, collection_name=name, exact=True)
        return int(result.count)

    def scroll_all(self, collection: str | None = None, page_size: int = 1000) -> list[tuple[str, dict]]:
        name = collection or self._collection
        records: list[tuple[str, dict]] = []
        offset: Any = None
        while True:
            points, next_offset = self._call(
                self._client.scroll,
                collection_name=name,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                records.append((str(point.id), point.payload or {}))
            if next_offset is None or not points:
                break
            offset = next_offset
        return records

    def semantic_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        conditions: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[RankedResult]:
        name = self._collection
        query = np.asarray(query_vector, dtype=np.float32).tolist()
        response = self._call(
            self._client.query_points,
            collection_name=name,
            query=query,
            query_filter=_build_filter(conditions),
            limit=top_k,
            with_payload=True,
            score_threshold=score_threshold,
        )
        results: list[RankedResult] = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                RankedResult(
                    chunk_id=payload.get("chunk_id", str(point.id)),
                    score=float(point.score),
                    payload=payload,
                    dense_score=float(point.score),
                )
            )
        return results

    def search(
        self,
        query: str,
        top_k: int = 10,
        conditions: dict[str, Any] | None = None,
    ) -> list[RankedResult]:
        name = self._collection
        try:
            response = self._call(
                self._client.query_points,
                collection_name=name,
                query=query,
                query_filter=_build_filter(conditions),
                limit=top_k,
                with_payload=True,
            )
        except ValueError as exc:
            self._logger.warning(
                "Full-text search unavailable on %s (local mode fallback): %s", name, exc
            )
            return []
        results: list[RankedResult] = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                RankedResult(
                    chunk_id=payload.get("chunk_id", str(point.id)),
                    score=float(point.score),
                    payload=payload,
                    lexical_score=float(point.score),
                )
            )
        return results

    def collection_info(self, collection: str | None = None) -> dict[str, Any]:
        name = collection or self._collection
        info = self._call(self._client.get_collection, collection_name=name)
        vectors_count = info.vectors_count
        if isinstance(vectors_count, dict):
            vectors_count = sum(vectors_count.values()) if vectors_count else 0
        return {
            "name": name,
            "status": str(info.status),
            "points": int(info.points_count),
            "vectors": int(vectors_count or 0),
            "indexed": int(info.indexed_vectors_count or 0),
        }
