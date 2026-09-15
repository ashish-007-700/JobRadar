from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import channel_service
from app.services.channel_service import ChannelValidationError

router = APIRouter()


class ChannelCreateRequest(BaseModel):
    channel: str


class ChannelUpdateRequest(BaseModel):
    enabled: bool


@router.get("/channels")
async def list_channels():
    return await channel_service.list_channels()


@router.post("/channels", status_code=201)
async def create_channel(payload: ChannelCreateRequest):
    try:
        return await channel_service.create_channel(payload.channel)
    except ChannelValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, payload: ChannelUpdateRequest):
    try:
        return await channel_service.update_channel_enabled(channel_id, payload.enabled)
    except ChannelValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    try:
        await channel_service.delete_channel(channel_id)
    except ChannelValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"status": "deleted", "id": channel_id}


@router.post("/channels/{channel_id}/validate")
async def validate_channel(channel_id: str):
    try:
        return await channel_service.revalidate_channel(channel_id)
    except ChannelValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
