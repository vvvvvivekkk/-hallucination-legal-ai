from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..core.utils import now_iso


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    progress: float = 0.0
    message: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


class JobManager:
    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._persist_path = Path(persist_path) if persist_path else None
        self._load()

    def create(self, kind: str, **params: Any) -> Job:
        job = Job(id=uuid.uuid4().hex, kind=kind, params=params)
        with self._lock:
            self._jobs[job.id] = job
            self._save()
        return job

    def update(self, job_id: str, **fields: Any) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown job: {job_id}")
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = now_iso()
            self._save()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def _save(self) -> None:
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(job) for job in self._jobs.values()]
        temp = self._persist_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        temp.replace(self._persist_path)

    def _load(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for item in payload:
            self._jobs[item["id"]] = Job(**item)
