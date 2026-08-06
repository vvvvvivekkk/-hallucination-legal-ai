from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from ..config import Settings
from ..core.exceptions import IngestionError
from ..core.logger import get_logger
from ..core.models import LegalMetadata, ParsedDocument
from ..core.utils import now_iso
from ..retrieval.bm25 import LocalBm25Index
from ..retrieval.qdrant import QdrantStore
from ..services.jobs import JobManager
from .chunker import SummaryAugmentedChunker
from .cleaner import TextCleaner
from .dedup import DuplicateDetector
from .embedder import Embedder
from .loader import DocumentLoader
from .metadata import extract_metadata
from .parser import PDFParser, TextParser, parse_source
from .summarizer import LegalSummarizer


@dataclass
class IngestTask:
    path: str
    collection: str | None = None
    enable_dedup: bool = True


@dataclass
class IndexTask:
    collection: str | None = None


@dataclass
class ReindexTask:
    collection: str | None = None
    path: str | None = None
    enable_dedup: bool = True


@dataclass
class IngestionReport:
    files_scanned: int = 0
    docs_ingested: int = 0
    docs_skipped_duplicate: int = 0
    docs_failed: int = 0
    chunks_uploaded: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IngestionPipeline:
    def __init__(
        self,
        settings: Settings,
        store: QdrantStore,
        embedder: Embedder,
        loader: DocumentLoader | None = None,
        pdf_parser: PDFParser | None = None,
        text_parser: TextParser | None = None,
        cleaner: TextCleaner | None = None,
        dedup: DuplicateDetector | None = None,
        chunker: SummaryAugmentedChunker | None = None,
        local_bm25: LocalBm25Index | None = None,
        logger: object | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._embedder = embedder
        self._logger = logger or get_logger(self.__class__.__name__)
        self._loader = loader or DocumentLoader(logger=self._logger)
        self._pdf_parser = pdf_parser or PDFParser(
            enable_ocr=settings.enable_ocr_fallback,
            ocr_min_chars=settings.ocr_min_chars,
            ocr_dpi=settings.ocr_dpi,
            logger=self._logger,
        )
        self._text_parser = text_parser or TextParser()
        self._cleaner = cleaner or TextCleaner()
        self._dedup = dedup or DuplicateDetector(
            store_path=settings.dedup_store_path,
            threshold=settings.dedup_threshold,
            logger=self._logger,
        )
        self._chunker = chunker or SummaryAugmentedChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            min_chunk_words=settings.chunk_min_words,
            enable_summary=settings.enable_summary_augment,
            embed_summary_augment=settings.embed_summary_augment,
            summarizer=LegalSummarizer(max_sentences=settings.summary_max_sentences),
            logger=self._logger,
        )
        self._local_bm25 = local_bm25

    def _collection(self, collection: str | None) -> str:
        return collection or self._settings.qdrant_collection

    def run(self, job_id: str, task: IngestTask, jobs: JobManager) -> IngestionReport:
        started = time.monotonic()
        collection = self._collection(task.collection)
        jobs.update(job_id, status="running", progress=0.0, message="Starting ingestion")
        report = IngestionReport()

        try:
            self._store.ensure_collection(collection)
            sources = self._loader.load(task.path)
            report.files_scanned = len(sources)
            if not sources:
                raise IngestionError(f"No supported documents found under {task.path}")

            for index, source in enumerate(sources):
                try:
                    document = parse_source(source, self._pdf_parser, self._text_parser)
                    document = self._cleaner.clean_document(document)
                    if task.enable_dedup:
                        is_duplicate, existing = self._dedup.is_duplicate(document.text)
                        if is_duplicate:
                            report.docs_skipped_duplicate += 1
                            self._logger.info(
                                "Skipping duplicate %s (ingested as %s)", source.filename, existing
                            )
                            continue
                    metadata: LegalMetadata = extract_metadata(document)
                    metadata.ingested_at = now_iso()
                    chunks = self._chunker.chunk(document, metadata)
                    if not chunks:
                        self._logger.warning("No chunks produced for %s", source.filename)
                        continue
                    embeddings = self._embedder.embed_chunks(chunks)
                    self._store.upsert_chunks(chunks, collection=collection, embeddings=embeddings)
                    if task.enable_dedup:
                        self._dedup.add(document.text, metadata.doc_id)
                    report.docs_ingested += 1
                    report.chunks_uploaded += len(chunks)
                    self._logger.info("Ingested %s -> %d chunks", source.filename, len(chunks))
                except Exception as exc:
                    report.docs_failed += 1
                    report.errors.append(f"{source.filename}: {exc}")
                    self._logger.exception("Failed to ingest %s", source.filename)

                progress = (index + 1) / len(sources)
                jobs.update(
                    job_id,
                    progress=round(progress, 4),
                    message=f"Ingesting {index + 1}/{len(sources)}",
                )

            if self._settings.bm25_backend == "local":
                self._rebuild_local_bm25(collection)
            self._dedup.save()
            report.elapsed_seconds = round(time.monotonic() - started, 2)
            jobs.update(
                job_id,
                status="completed",
                progress=1.0,
                message="Ingestion completed",
                stats=report.to_dict(),
            )
        except Exception as exc:
            report.elapsed_seconds = round(time.monotonic() - started, 2)
            self._logger.exception("Ingestion failed")
            jobs.update(
                job_id,
                status="failed",
                message="Ingestion failed",
                error=str(exc),
                stats=report.to_dict(),
            )
        return report

    def index(self, job_id: str, task: IndexTask, jobs: JobManager) -> dict[str, Any]:
        collection = self._collection(task.collection)
        jobs.update(job_id, status="running", progress=0.0, message="Building indexes")
        try:
            self._store.ensure_collection(collection)
            if self._settings.bm25_backend == "local":
                self._rebuild_local_bm25(collection)
            info = self._store.collection_info(collection)
            jobs.update(
                job_id,
                status="completed",
                progress=1.0,
                message="Indexes ready",
                stats={"collection": info},
            )
            return info
        except Exception as exc:
            self._logger.exception("Index build failed")
            jobs.update(job_id, status="failed", message="Index build failed", error=str(exc))
            raise

    def reindex(self, job_id: str, task: ReindexTask, jobs: JobManager) -> dict[str, Any]:
        collection = self._collection(task.collection)
        jobs.update(job_id, status="running", progress=0.0, message="Reindexing collection")
        try:
            self._store.delete_collection(collection)
            self._store.ensure_collection(collection)
            if task.path:
                ingest_task = IngestTask(
                    path=task.path,
                    collection=collection,
                    enable_dedup=task.enable_dedup,
                )
                report = self.run(job_id, ingest_task, jobs).to_dict()
                return report
            if self._settings.bm25_backend == "local":
                self._rebuild_local_bm25(collection)
            jobs.update(
                job_id,
                status="completed",
                progress=1.0,
                message="Reindex completed",
                stats={"collection": self._store.collection_info(collection)},
            )
            return {"collection": collection}
        except Exception as exc:
            self._logger.exception("Reindex failed")
            jobs.update(job_id, status="failed", message="Reindex failed", error=str(exc))
            raise

    def _rebuild_local_bm25(self, collection: str) -> None:
        index = self._local_bm25 or LocalBm25Index(
            k1=self._settings.bm25_k1,
            b=self._settings.bm25_b,
            store_path=self._settings.bm25_local_path,
            logger=self._logger,
        )
        entries: list[tuple[str, str, dict[str, Any]]] = []
        for _, payload in self._store.scroll_all(collection):
            chunk_text = payload.get("chunk_text")
            if chunk_text:
                entries.append((payload["chunk_id"], chunk_text, payload))
        index.build(entries)
        index.save()
        self._logger.info("Rebuilt local BM25 index with %d entries", len(entries))
