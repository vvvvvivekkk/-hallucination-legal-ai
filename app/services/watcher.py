from __future__ import annotations

import asyncio
import time
from pathlib import Path

from ..api.dependencies import get_jobs, get_pipeline
from ..config import Settings
from ..core.logger import get_logger

logger = get_logger(__name__)


class WatchState:
    def __init__(self) -> None:
        self._seen: dict[Path, float] = {}
        self._ingesting: set[str] = set()

    def mark_seen(self, path: Path) -> None:
        self._seen[path] = time.time()
        if len(self._seen) > 10_000:
            oldest = min(self._seen, key=self._seen.get)
            self._seen.pop(oldest, None)

    def is_new(self, path: Path, settle_seconds: float = 2.0) -> bool:
        stamp = self._seen.get(path)
        return stamp is not None and (time.time() - stamp) >= settle_seconds

    def claim(self, path: Path) -> bool:
        key = str(path.resolve())
        if key in self._ingesting:
            return False
        self._ingesting.add(key)
        return True

    def release(self, path: Path) -> None:
        self._ingesting.discard(str(path.resolve()))


class AutoIngestWatcher:
    """Periodically scans a watch directory and ingests new documents."""

    def __init__(self, settings: Settings, interval: float = 10.0) -> None:
        self._settings = settings
        self._dir = Path(settings.auto_ingest_watch_dir)
        self._interval = interval
        self._state = WatchState()
        self._task: asyncio.Task | None = None
        self._pipeline = None
        self._stopping = False

    async def start(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        for path in self._dir.iterdir():
            if path.is_file():
                self._state.mark_seen(path)
        self._task = asyncio.create_task(self._run())
        logger.info("Auto-ingest watcher started on %s", self._dir)

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-ingest watcher stopped")

    async def _run(self) -> None:
        while not self._stopping:
            try:
                await self.scan_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("auto-ingest scan failed")
            await asyncio.sleep(self._interval)

    async def scan_once(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        candidates: list[Path] = []
        for path in sorted(self._dir.iterdir()):
            if not path.is_file():
                continue
            self._state.mark_seen(path)
            if self._state.is_new(path):
                candidates.append(path)
        for path in candidates:
            if self._state.claim(path):
                try:
                    await self._ingest(path)
                finally:
                    self._state.release(path)

    async def _ingest(self, path: Path) -> None:
        logger.info("Auto-ingesting %s", path.name)
        try:
            from starlette.concurrency import run_in_threadpool

            from ..ingestion.pipeline import IngestTask

            pipeline = get_pipeline()
            jobs = get_jobs()
            job = jobs.create(
                kind="ingest",
                path=str(path),
                collection=None,
                enable_dedup=True,
            )
            report = await run_in_threadpool(pipeline.run, job.id, IngestTask(path=str(path)), jobs)
            logger.info(
                "Ingested %s: %d chunks, %d files",
                path.name,
                getattr(report, "chunks_uploaded", 0),
                getattr(report, "files_scanned", 0),
            )
        except Exception:
            logger.exception("failed to auto-ingest %s", path.name)


_watcher: AutoIngestWatcher | None = None


async def start_watcher() -> AutoIngestWatcher:
    global _watcher
    if _watcher is not None:
        return _watcher
    settings = Settings()
    _watcher = AutoIngestWatcher(settings, interval=float(settings.auto_ingest_interval_seconds))
    await _watcher.start()
    return _watcher
