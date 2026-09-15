from fastapi import APIRouter
from pydantic import BaseModel

from app.services import url_resolver

router = APIRouter()


class ResolveUrlRequest(BaseModel):
    url: str


@router.post("/resolve-url")
async def resolve_url(payload: ResolveUrlRequest):
    return await url_resolver.resolve_apply_url(payload.url)
