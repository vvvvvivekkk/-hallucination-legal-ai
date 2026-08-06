from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ...config import Settings
from ...ingestion.pipeline import (
    IndexTask,
    IngestionPipeline,
    IngestTask,
    ReindexTask,
)
from ...services.jobs import JobManager
from ..dependencies import get_jobs, get_pipeline, get_settings
from ..schemas import (
    IndexRequest,
    IngestRequest,
    IngestResponse,
    JobResponse,
    ReindexRequest,
)

router = APIRouter(prefix="/api", tags=["ingestion"])


@router.post("/ingest", status_code=202, response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    jobs: JobManager = Depends(get_jobs),
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> IngestResponse:
    path = request.path or settings.ingestion_dir
    if not Path(path).exists():
        raise HTTPException(status_code=400, detail=f"Ingestion path does not exist: {path}")
    task = IngestTask(path=path, collection=request.collection, enable_dedup=request.enable_dedup)
    job = jobs.create(
        kind="ingest",
        path=path,
        collection=task.collection,
        enable_dedup=task.enable_dedup,
    )
    background_tasks.add_task(pipeline.run, job.id, task, jobs)
    return IngestResponse(job_id=job.id, status=job.status, message="Ingestion queued")


@router.post("/index", status_code=202, response_model=IngestResponse)
async def index(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    jobs: JobManager = Depends(get_jobs),
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> IngestResponse:
    task = IndexTask(collection=request.collection)
    job = jobs.create(kind="index", collection=task.collection)
    background_tasks.add_task(pipeline.index, job.id, task, jobs)
    return IngestResponse(job_id=job.id, status=job.status, message="Index build queued")


@router.post("/reindex", status_code=202, response_model=IngestResponse)
async def reindex(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
    jobs: JobManager = Depends(get_jobs),
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> IngestResponse:
    task = ReindexTask(
        collection=request.collection,
        path=request.path,
        enable_dedup=request.enable_dedup,
    )
    job = jobs.create(
        kind="reindex",
        collection=task.collection,
        path=task.path,
        enable_dedup=task.enable_dedup,
    )
    background_tasks.add_task(pipeline.reindex, job.id, task, jobs)
    return IngestResponse(job_id=job.id, status=job.status, message="Reindex queued")


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(jobs: JobManager = Depends(get_jobs)) -> list[JobResponse]:
    return [
        JobResponse(
            job_id=job.id,
            kind=job.kind,
            status=job.status,
            progress=job.progress,
            message=job.message,
            error=job.error,
            stats=job.stats,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        for job in jobs.list()
    ]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, jobs: JobManager = Depends(get_jobs)) -> JobResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JobResponse(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error,
        stats=job.stats,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
