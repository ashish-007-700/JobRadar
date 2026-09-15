from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.services import message_service
from app.services.message_service import FetchValidationError

router = APIRouter()


class TelegramFetchRequest(BaseModel):
    date: str | None = None


@router.post("/telegram/fetch")
async def fetch_telegram_messages(payload: TelegramFetchRequest | None = Body(default=None)):
    date_str = payload.date if payload else None
    try:
        return await message_service.fetch_messages_for_date(date_str)
    except FetchValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
