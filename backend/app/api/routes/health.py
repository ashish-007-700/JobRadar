from fastapi import APIRouter

from app.services.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/health/db")
def health_check_db():
    try:
        client = get_supabase_client()
        client.table("channels").select("id").limit(1).execute()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    return {"status": "ok"}
