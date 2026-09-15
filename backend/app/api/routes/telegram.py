from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.services import fetch_run_service, message_service
from app.services.fetch_run_service import FetchRunError
from app.services.message_service import FetchValidationError

router = APIRouter()

RUN_STATUS_TO_STATE = {
    "completed": "completed",
    "completed_with_errors": "partial",
    "failed": "failed",
}


class TelegramFetchRequest(BaseModel):
    date: str | None = None
    resolve_urls: bool = False
    save_jobs: bool = False


@router.post("/telegram/fetch")
async def fetch_telegram_messages(payload: TelegramFetchRequest | None = Body(default=None)):
    date_str = payload.date if payload else None
    resolve_urls = payload.resolve_urls if payload else False
    save_jobs = payload.save_jobs if payload else False
    try:
        return await message_service.fetch_messages_for_date(
            date_str, resolve_urls=resolve_urls, save_jobs=save_jobs
        )
    except FetchValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/telegram/fetch/status")
async def fetch_status():
    if message_service.is_fetch_running():
        return {"state": "running", "last_run": None}

    try:
        runs = fetch_run_service.list_fetch_runs(limit=1)
    except FetchRunError:
        return {"state": "idle", "last_run": None}

    if not runs:
        return {"state": "idle", "last_run": None}

    last_run = runs[0]
    state = RUN_STATUS_TO_STATE.get(last_run["status"], "failed")
    return {"state": state, "last_run": last_run}
