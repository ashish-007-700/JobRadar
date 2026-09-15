import logging
from collections import defaultdict
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from postgrest.exceptions import APIError
from telethon.errors import RPCError

from app.config import APP_TIMEZONE
from app.services import channel_service, job_detection, job_service, telegram_client, url_resolver
from app.services.job_service import JobStorageError
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

RESOLUTION_ERROR_MESSAGES = {
    "timeout": "Timed out while resolving an application URL.",
    "http_error": "Unable to reach the application page while resolving the URL.",
    "blocked": "The application URL was blocked for security reasons.",
    "invalid_url": "The application URL was invalid.",
    "resolution_error": "An unexpected error occurred while resolving the application URL.",
}

# Process-local guard: this is a single-instance personal app, so a plain flag
# (checked and set with no `await` in between, safe under asyncio's
# single-threaded cooperative scheduling) is enough to stop a second fetch from
# starting while one is already running. No distributed locking needed.
_fetch_in_progress = False


class FetchValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def is_fetch_running() -> bool:
    return _fetch_in_progress


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
    try:
        result = (
            client.table("fetch_runs")
            .insert({"requested_date": requested_date.isoformat(), "status": "running"})
            .execute()
        )
    except APIError as exc:
        raise FetchValidationError(str(exc), status_code=502) from exc
    return result.data[0]


def _finish_fetch_run(run_id: str, **fields) -> None:
    # Recording the outcome is bookkeeping, not the result itself: if Supabase
    # hiccups here, log it but still let the caller return the real fetch
    # result/error to the user instead of masking it with this failure.
    try:
        client = get_supabase_client()
        client.table("fetch_runs").update(fields).eq("id", run_id).execute()
    except (RuntimeError, APIError) as exc:
        logger.warning("Failed to update fetch_runs %s: %s", run_id, exc)


async def _resolve_job_urls(jobs: list[dict]) -> list[dict]:
    resolution_errors = []
    async with httpx.AsyncClient() as client:
        for job in jobs:
            original_url = job.get("original_apply_url")
            if not original_url:
                continue
            result = await url_resolver.resolve_apply_url(original_url, client=client)
            job["final_apply_url"] = result["final_apply_url"]
            job["resolution_status"] = result["resolution_status"]
            friendly = RESOLUTION_ERROR_MESSAGES.get(result["resolution_status"])
            if friendly:
                resolution_errors.append(
                    {
                        "telegram_channel": job.get("telegram_channel"),
                        "telegram_message_id": job.get("telegram_message_id"),
                        "detail": friendly,
                    }
                )
    return resolution_errors


def _save_jobs(jobs: list[dict]) -> tuple[int, int, list[dict]]:
    saved_count = 0
    duplicate_count = 0
    save_errors = []
    for job in jobs:
        channel = job.get("telegram_channel")
        message_id = job.get("telegram_message_id")

        try:
            already_saved = channel and message_id is not None and job_service.job_exists(
                channel, message_id
            )
        except JobStorageError:
            # If the existence check itself fails, don't silently drop the
            # job - fall through and attempt the insert anyway.
            already_saved = False

        if already_saved:
            job["saved"] = False
            job["duplicate"] = True
            duplicate_count += 1
            continue

        try:
            saved_row = job_service.save_job(job)
        except JobStorageError as exc:
            job["saved"] = False
            save_errors.append(
                {
                    "telegram_channel": channel,
                    "telegram_message_id": message_id,
                    "detail": exc.message,
                }
            )
        else:
            job["id"] = saved_row["id"]
            job["saved"] = True
            saved_count += 1
    return saved_count, duplicate_count, save_errors


def _add_per_channel_job_stats(channel_results: list[dict], detected_jobs: list[dict]) -> None:
    jobs_detected_by_channel = defaultdict(int)
    jobs_saved_by_channel = defaultdict(int)
    for job in detected_jobs:
        channel = job.get("telegram_channel")
        jobs_detected_by_channel[channel] += 1
        if job.get("saved"):
            jobs_saved_by_channel[channel] += 1

    for entry in channel_results:
        username = entry["channel_username"]
        entry["jobs_detected"] = jobs_detected_by_channel.get(username, 0)
        entry["jobs_saved"] = jobs_saved_by_channel.get(username, 0)


async def fetch_messages_for_date(
    date_str: str | None, resolve_urls: bool = False, save_jobs: bool = False
) -> dict:
    global _fetch_in_progress
    if _fetch_in_progress:
        raise FetchValidationError(
            "A fetch is already running. Please wait for it to finish.", status_code=409
        )

    _fetch_in_progress = True
    try:
        return await _run_fetch(date_str, resolve_urls, save_jobs)
    finally:
        _fetch_in_progress = False


async def _run_fetch(date_str: str | None, resolve_urls: bool, save_jobs: bool) -> dict:
    requested_date, start_utc, end_utc = _resolve_date_window(date_str)

    channels = await channel_service.list_channels()
    enabled_channels = [c for c in channels if c.get("enabled")]

    run = _create_fetch_run(requested_date)

    try:
        client = telegram_client.get_client()
    except RuntimeError as exc:
        message = "Telegram authentication is unavailable. Run the login script first."
        _finish_fetch_run(
            run["id"],
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            errors=[{"detail": message}],
        )
        raise FetchValidationError(message, status_code=503) from exc

    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        message = "Telegram authentication is unavailable. Run the login script first."
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
            detail = f"Unable to access channel @{username}."
            channel_results.append(
                {"channel_username": username, "messages_processed": 0, "status": "error", "error": detail}
            )
            run_errors.append({"channel_username": username, "detail": detail})
        except Exception:
            detail = f"Unexpected error while fetching channel @{username}."
            channel_results.append(
                {"channel_username": username, "messages_processed": 0, "status": "error", "error": detail}
            )
            run_errors.append({"channel_username": username, "detail": detail})
        else:
            channel_results.append(
                {
                    "channel_username": username,
                    "messages_processed": len(channel_messages),
                    "status": "ok",
                }
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
        resolution_errors = await _resolve_job_urls(detected_jobs)
        run_errors.extend(resolution_errors)
        logger.info("Resolved apply URLs for %d detected jobs", len(detected_jobs))

    jobs_saved = 0
    jobs_duplicate = 0
    if save_jobs and detected_jobs:
        jobs_saved, jobs_duplicate, save_errors = _save_jobs(detected_jobs)
        run_errors.extend(save_errors)
        logger.info(
            "Saved %d/%d detected jobs (%d already saved previously)",
            jobs_saved,
            len(detected_jobs),
            jobs_duplicate,
        )

    _add_per_channel_job_stats(channel_results, detected_jobs)

    status = "completed_with_errors" if run_errors else "completed"
    _finish_fetch_run(
        run["id"],
        status=status,
        completed_at=datetime.now(timezone.utc).isoformat(),
        channels_processed=len(enabled_channels),
        messages_processed=len(all_messages),
        jobs_detected=len(detected_jobs),
        jobs_saved=jobs_saved,
        errors=run_errors,
    )

    return {
        "date": requested_date.isoformat(),
        "status": status,
        "channels_processed": len(enabled_channels),
        "messages_found": len(all_messages),
        "jobs_detected": len(detected_jobs),
        "jobs_saved": jobs_saved,
        "jobs_duplicate": jobs_duplicate,
        "errors": run_errors,
        "channel_results": channel_results,
        "messages": all_messages,
        "jobs": detected_jobs,
    }
