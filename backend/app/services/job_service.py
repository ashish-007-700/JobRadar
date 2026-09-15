from datetime import date as date_cls
from datetime import timedelta

from postgrest.exceptions import APIError

from app.services.supabase_client import get_supabase_client

JOB_COLUMNS = [
    "company",
    "title",
    "location",
    "experience",
    "qualification",
    "batch",
    "salary",
    "skills",
    "employment_type",
    "telegram_message_id",
    "telegram_channel",
    "telegram_message_url",
    "original_apply_url",
    "final_apply_url",
    "posted_at",
]


class JobStorageError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_client():
    try:
        return get_supabase_client()
    except RuntimeError as exc:
        raise JobStorageError(str(exc), status_code=503) from exc


def _to_row(job: dict) -> dict:
    return {column: job.get(column) for column in JOB_COLUMNS}


def _validate_job(job: dict) -> None:
    if not job.get("telegram_channel") or job.get("telegram_message_id") is None:
        raise JobStorageError("Job is missing required Telegram metadata.", status_code=400)

    for field in ("original_apply_url", "final_apply_url"):
        value = job.get(field)
        if value and not (value.startswith("http://") or value.startswith("https://")):
            raise JobStorageError(f"Invalid URL in field '{field}'.", status_code=400)


def save_job(job: dict) -> dict:
    _validate_job(job)
    client = _get_client()
    row = _to_row(job)

    try:
        result = client.table("jobs").insert(row).execute()
    except APIError as exc:
        raise JobStorageError(str(exc), status_code=500) from exc
    except Exception as exc:
        raise JobStorageError(str(exc), status_code=500) from exc

    if not result.data:
        raise JobStorageError("Insert returned no data.", status_code=500)
    return result.data[0]


def list_jobs(
    date: str | None = None,
    company: str | None = None,
    location: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    client = _get_client()
    query = client.table("jobs").select("*")

    if date:
        try:
            requested_date = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise JobStorageError(f"Invalid date '{date}'. Use YYYY-MM-DD.", status_code=400) from exc
        next_day = requested_date + timedelta(days=1)
        query = query.gte("posted_at", f"{requested_date.isoformat()}T00:00:00+00:00")
        query = query.lt("posted_at", f"{next_day.isoformat()}T00:00:00+00:00")

    if company:
        query = query.ilike("company", f"%{company}%")
    if location:
        query = query.ilike("location", f"%{location}%")

    query = query.order("posted_at", desc=True).range(offset, offset + limit - 1)

    try:
        result = query.execute()
    except APIError as exc:
        raise JobStorageError(str(exc), status_code=500) from exc
    return result.data


def get_job(job_id: str) -> dict | None:
    client = _get_client()
    try:
        result = client.table("jobs").select("*").eq("id", job_id).execute()
    except APIError as exc:
        raise JobStorageError(str(exc), status_code=500) from exc
    return result.data[0] if result.data else None
