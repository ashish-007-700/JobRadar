import asyncio
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import fetch_run_service, message_service

client = TestClient(app)


# Fetch already running -----------------------------------------------------------------


def test_fetch_messages_for_date_rejects_concurrent_run(monkeypatch):
    monkeypatch.setattr(message_service, "_fetch_in_progress", True)

    with pytest.raises(message_service.FetchValidationError) as exc_info:
        asyncio.run(message_service.fetch_messages_for_date("2026-09-15"))

    assert exc_info.value.status_code == 409
    assert "already running" in exc_info.value.message.lower()


def test_is_fetch_running_reflects_flag(monkeypatch):
    monkeypatch.setattr(message_service, "_fetch_in_progress", False)
    assert message_service.is_fetch_running() is False

    monkeypatch.setattr(message_service, "_fetch_in_progress", True)
    assert message_service.is_fetch_running() is True


def test_fetch_flag_is_cleared_even_when_run_raises(monkeypatch):
    async def failing_run(date_str, resolve_urls, save_jobs):
        raise RuntimeError("boom")

    monkeypatch.setattr(message_service, "_run_fetch", failing_run)

    with pytest.raises(RuntimeError):
        asyncio.run(message_service.fetch_messages_for_date("2026-09-15"))

    assert message_service.is_fetch_running() is False


# GET /api/fetch-runs ---------------------------------------------------------------------


def test_list_fetch_runs_endpoint(monkeypatch):
    monkeypatch.setattr(
        fetch_run_service,
        "list_fetch_runs",
        lambda limit=20: [{"id": "run-1", "status": "completed"}],
    )

    response = client.get("/api/fetch-runs")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "run-1"


def test_list_fetch_runs_endpoint_forwards_limit(monkeypatch):
    captured = {}

    def fake_list(limit=20):
        captured["limit"] = limit
        return []

    monkeypatch.setattr(fetch_run_service, "list_fetch_runs", fake_list)

    client.get("/api/fetch-runs?limit=5")

    assert captured["limit"] == 5


# GET /api/telegram/fetch/status -----------------------------------------------------------


def test_fetch_status_running(monkeypatch):
    monkeypatch.setattr(message_service, "is_fetch_running", lambda: True)

    response = client.get("/api/telegram/fetch/status")

    assert response.status_code == 200
    assert response.json()["state"] == "running"


def test_fetch_status_idle_when_no_runs(monkeypatch):
    monkeypatch.setattr(message_service, "is_fetch_running", lambda: False)
    monkeypatch.setattr(fetch_run_service, "list_fetch_runs", lambda limit=1: [])

    response = client.get("/api/telegram/fetch/status")

    assert response.json() == {"state": "idle", "last_run": None}


@pytest.mark.parametrize(
    "run_status,expected_state",
    [
        ("completed", "completed"),
        ("completed_with_errors", "partial"),
        ("failed", "failed"),
        ("running", "failed"),  # a stuck row from a crashed process
    ],
)
def test_fetch_status_maps_last_run_status(monkeypatch, run_status, expected_state):
    monkeypatch.setattr(message_service, "is_fetch_running", lambda: False)
    monkeypatch.setattr(
        fetch_run_service, "list_fetch_runs", lambda limit=1: [{"id": "run-1", "status": run_status}]
    )

    response = client.get("/api/telegram/fetch/status")

    assert response.json()["state"] == expected_state
    assert response.json()["last_run"]["id"] == "run-1"


# Per-channel job stats -------------------------------------------------------------------


def test_add_per_channel_job_stats():
    channel_results = [
        {"channel_username": "a", "messages_processed": 3, "status": "ok"},
        {"channel_username": "b", "messages_processed": 0, "status": "error", "error": "oops"},
    ]
    detected_jobs = [
        {"telegram_channel": "a", "saved": True},
        {"telegram_channel": "a", "saved": False},
    ]

    message_service._add_per_channel_job_stats(channel_results, detected_jobs)

    assert channel_results[0]["jobs_detected"] == 2
    assert channel_results[0]["jobs_saved"] == 1
    assert channel_results[1]["jobs_detected"] == 0
    assert channel_results[1]["jobs_saved"] == 0


# Friendly resolution error surfacing -----------------------------------------------------


def test_resolve_job_urls_surfaces_friendly_timeout_message(monkeypatch):
    async def fake_resolve(url, client=None):
        return {"final_apply_url": url, "resolution_status": "timeout"}

    monkeypatch.setattr(message_service.url_resolver, "resolve_apply_url", fake_resolve)

    jobs = [{"original_apply_url": "https://example.com/apply", "telegram_channel": "a", "telegram_message_id": 1}]
    errors = asyncio.run(message_service._resolve_job_urls(jobs))

    assert len(errors) == 1
    assert errors[0]["detail"] == "Timed out while resolving an application URL."


def test_resolve_job_urls_no_error_for_normal_outcomes(monkeypatch):
    async def fake_resolve(url, client=None):
        return {"final_apply_url": url, "resolution_status": "no_next_link"}

    monkeypatch.setattr(message_service.url_resolver, "resolve_apply_url", fake_resolve)

    jobs = [{"original_apply_url": "https://example.com/apply", "telegram_channel": "a", "telegram_message_id": 1}]
    errors = asyncio.run(message_service._resolve_job_urls(jobs))

    assert errors == []


# Date/timezone handling ------------------------------------------------------------------


def test_resolve_date_window_assigns_near_midnight_message_correctly(monkeypatch):
    monkeypatch.setattr(message_service, "APP_TIMEZONE", "Asia/Kolkata")
    requested_date, start_utc, end_utc = message_service._resolve_date_window("2026-09-15")

    # IST is UTC+5:30, so a message just after midnight IST on the 15th falls on
    # the 14th in UTC. Naively filtering by UTC calendar date would wrongly
    # exclude it from "the 15th"; the timezone-aware window must still include it.
    just_after_midnight_ist = datetime(2026, 9, 15, 0, 10, tzinfo=ZoneInfo("Asia/Kolkata"))
    just_after_midnight_utc = just_after_midnight_ist.astimezone(timezone.utc)

    assert start_utc <= just_after_midnight_utc < end_utc
    assert just_after_midnight_utc.date() == date(2026, 9, 14)  # wrong day under naive UTC filtering


def test_resolve_date_window_excludes_previous_day_late_utc_message(monkeypatch):
    monkeypatch.setattr(message_service, "APP_TIMEZONE", "Asia/Kolkata")
    requested_date, start_utc, end_utc = message_service._resolve_date_window("2026-09-15")

    # A message at 2026-09-14 19:00 UTC is 2026-09-15 00:30 IST -> belongs to the 15th.
    just_after_midnight_ist_utc = datetime(2026, 9, 14, 19, 0, tzinfo=timezone.utc)
    assert start_utc <= just_after_midnight_ist_utc < end_utc

    # But 2026-09-14 18:00 UTC is 2026-09-14 23:30 IST -> belongs to the 14th, excluded.
    still_previous_day_utc = datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc)
    assert not (start_utc <= still_previous_day_utc < end_utc)
