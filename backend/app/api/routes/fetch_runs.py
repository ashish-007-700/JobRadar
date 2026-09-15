from fastapi import APIRouter, HTTPException, Query

from app.services import fetch_run_service
from app.services.fetch_run_service import FetchRunError

router = APIRouter()


@router.get("/fetch-runs")
async def list_fetch_runs(limit: int = Query(default=20, ge=1, le=50)):
    try:
        return fetch_run_service.list_fetch_runs(limit=limit)
    except FetchRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
