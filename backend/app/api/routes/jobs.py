from fastapi import APIRouter, HTTPException, Query

from app.services import job_service
from app.services.job_service import JobStorageError

router = APIRouter()


@router.get("/jobs")
async def list_jobs(
    date: str | None = Query(default=None),
    company: str | None = Query(default=None),
    location: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    try:
        return job_service.list_jobs(date=date, company=company, location=location, limit=limit, offset=offset)
    except JobStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        job = job_service.get_job(job_id)
    except JobStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
