from app.services.supabase_client import get_supabase_client


class FetchRunError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_client():
    try:
        return get_supabase_client()
    except RuntimeError as exc:
        raise FetchRunError(str(exc), status_code=503) from exc


def list_fetch_runs(limit: int = 20) -> list[dict]:
    client = _get_client()
    result = (
        client.table("fetch_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
