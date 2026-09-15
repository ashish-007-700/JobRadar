import logging
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from telethon.errors import RPCError

from app.config import APP_TIMEZONE
from app.services import channel_service, job_detection, telegram_client, url_resolver
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class FetchValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _resolve_date_window(date_str: str | None) -> tuple[date_cls, datetime, datetime]:
    tz = ZoneInfo(APP_TIMEZONE)
    if date_str:
        try:
            requested_date = date_cls.fromisoformat(date_str)
        except ValueError as exc:
            raise FetchValidationError(f"Invalid date '{date_str}'. Use YYYY-MM-DD.") from exc
    else:
        requested_date = datetime.now(tz).date()

    start_local = datetime.combine(requested_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return requested_date, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _normalize_message(message, channel) -> dict:
    username = channel["channel_username"]
    return {
        "message_id": message.id,
        "channel_id": channel.get("telegram_channel_id"),
        "channel_username": username,
        "message_text": message.message or None,
        "message_date": message.date.isoformat(),
        "message_url": f"https://t.me/{username}/{message.id}",
    }


async def _fetch_channel_messages(client, channel: dict, start_utc: datetime, end_utc: datetime) -> list[dict]:
    username = channel["channel_username"]
    messages = []
    async for message in client.iter_messages(username, offset_date=end_utc):
        if message.date < start_utc:
            break
        if message.date >= end_utc:
            continue
        messages.append(_normalize_message(message, channel))
    return messages


def _create_fetch_run(requested_date: date_cls) -> dict:
    client = get_supabase_client()
    result = (
        client.table("fetch_runs")
        .insert({"requested_date": requested_date.isoformat(), "status": "running"})
        .execute()
    )
    return result.data[0]


def _finish_fetch_run(run_id: str, **fields) -> None:
    client = get_supabase_client()
    client.table("fetch_runs").update(fields).eq("id", run_id).execute()


async def _resolve_job_urls(jobs: list[dict]) -> None:
    async with httpx.AsyncClient() as client:
        for job in jobs:
            original_url = job.get("original_apply_url")
            if not original_url:
                continue
            result = await url_resolver.resolve_apply_url(original_url, client=client)
            job["final_apply_url"] = result["final_apply_url"]
            job["resolution_status"] = result["resolution_status"]


async def fetch_messages_for_date(date_str: str | None, resolve_urls: bool = False) -> dict:
    requested_date, start_utc, end_utc = _resolve_date_window(date_str)

    channels = await channel_service.list_channels()
    enabled_channels = [c for c in channels if c.get("enabled")]

    run = _create_fetch_run(requested_date)

    try:
        client = telegram_client.get_client()
    except RuntimeError as exc:
        _finish_fetch_run(
            run["id"],
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            errors=[{"detail": str(exc)}],
        )
        raise FetchValidationError(str(exc), status_code=503) from exc

    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        message = "Telegram authentication unavailable. Run the login script first."
        _finish_fetch_run(
            run["id"],
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            errors=[{"detail": message}],
        )
        raise FetchValidationError(message, status_code=503)

    channel_results = []
    all_messages = []
    run_errors = []

    for channel in enabled_channels:
        username = channel["channel_username"]
        try:
            channel_messages = await _fetch_channel_messages(client, channel, start_utc, end_utc)
        except RPCError:
            detail = "Telegram API error while fetching this channel."
            channel_results.append(
                {"channel_username": username, "message_count": 0, "status": "error", "detail": detail}
            )
            run_errors.append({"channel_username": username, "detail": detail})
        except Exception:
            detail = "Unexpected error while fetching this channel."
            channel_results.append(
                {"channel_username": username, "message_count": 0, "status": "error", "detail": detail}
            )
            run_errors.append({"channel_username": username, "detail": detail})
        else:
            channel_results.append(
                {"channel_username": username, "message_count": len(channel_messages), "status": "ok"}
            )
            all_messages.extend(channel_messages)

    detected_jobs = [
        job for job in (job_detection.process_message(m) for m in all_messages) if job is not None
    ]
    logger.info(
        "Fetch %s: %d messages, %d detected as jobs, %d rejected",
        requested_date,
        len(all_messages),
        len(detected_jobs),
        len(all_messages) - len(detected_jobs),
    )

    if resolve_urls and detected_jobs:
        await _resolve_job_urls(detected_jobs)
        logger.info("Resolved apply URLs for %d detected jobs", len(detected_jobs))

    status = "completed_with_errors" if run_errors else "completed"
    _finish_fetch_run(
        run["id"],
        status=status,
        completed_at=datetime.now(timezone.utc).isoformat(),
        channels_processed=len(enabled_channels),
        messages_processed=len(all_messages),
        jobs_detected=len(detected_jobs),
        errors=run_errors,
    )

    return {
        "date": requested_date.isoformat(),
        "channels_processed": len(enabled_channels),
        "messages_found": len(all_messages),
        "jobs_detected": len(detected_jobs),
        "channel_results": channel_results,
        "messages": all_messages,
        "jobs": detected_jobs,
    }
