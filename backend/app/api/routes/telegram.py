from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.services import message_service
from app.services.message_service import FetchValidationError

router = APIRouter()


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
