from __future__ import annotations

from app.config import Settings
from app.ingestion.pipeline import IngestionPipeline, IngestTask
from app.services.jobs import JobManager

from tests.conftest import FakeEmbedder, FakeStoreWithUpsert


def test_pipeline_ingests_txt(tmp_path) -> None:
    document = tmp_path / "act.txt"
    document.write_text("Section 300 defines murder. Punishment for murder is life imprisonment. " * 20)

    settings = Settings()
    settings.ingestion_dir = str(tmp_path)
    settings.dedup_store_path = str(tmp_path / "dedup.json")
    settings.bm25_local_path = str(tmp_path / "bm25.pkl")
    settings.bm25_backend = "local"

    store = FakeStoreWithUpsert()
    embedder = FakeEmbedder()
    jobs = JobManager()
    job = jobs.create("ingest", path=str(tmp_path))

    pipeline = IngestionPipeline(settings=settings, store=store, embedder=embedder)
    report = pipeline.run(job.id, IngestTask(path=str(tmp_path)), jobs)

    assert report.files_scanned == 1
    assert report.docs_ingested == 1
    assert report.chunks_uploaded > 0
    assert store.upsert_calls == 1
    assert jobs.get(job.id).status == "completed"
    assert jobs.get(job.id).stats["chunks_uploaded"] == report.chunks_uploaded


def test_pipeline_dedup_skips_duplicate(tmp_path) -> None:
    document = tmp_path / "act.txt"
    content = "Section 302 prescribes punishment for murder. " * 20
    document.write_text(content)

    settings = Settings()
    settings.dedup_store_path = str(tmp_path / "dedup.json")
    settings.bm25_local_path = str(tmp_path / "bm25.pkl")
    settings.bm25_backend = "local"

    store = FakeStoreWithUpsert()
    embedder = FakeEmbedder()
    jobs = JobManager()

    pipeline = IngestionPipeline(settings=settings, store=store, embedder=embedder)
    first = pipeline.run(jobs.create("ingest").id, IngestTask(path=str(tmp_path)), jobs)
    second = pipeline.run(jobs.create("ingest").id, IngestTask(path=str(tmp_path)), jobs)

    assert first.docs_ingested == 1
    assert second.docs_ingested == 0
    assert second.docs_skipped_duplicate == 1
    assert store.upsert_calls == 1
