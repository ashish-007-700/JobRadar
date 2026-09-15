from types import SimpleNamespace

import pytest

from app.services import job_service
from app.services.job_service import JobStorageError
from tests.fakes import FakeSupabaseClient


def make_job(**overrides) -> dict:
    job = {
        "company": "Acme Corp",
        "title": "Software Engineer",
        "location": "Bangalore",
        "experience": "0-2 years",
        "qualification": "B.Tech",
        "batch": "2026",
        "salary": "6 LPA",
        "skills": ["Python", "SQL"],
        "employment_type": "Full-time",
        "telegram_message_id": 42,
        "telegram_channel": "testchannel",
        "telegram_message_url": "https://t.me/testchannel/42",
        "original_apply_url": "https://acme.com/apply",
        "final_apply_url": None,
        "posted_at": "2026-09-15T09:00:00+00:00",
    }
    job.update(overrides)
    return job


# 1. Successful job insertion -------------------------------------------------------


def test_save_job_success(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "job-1", **make_job()}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    result = job_service.save_job(make_job())

    assert result["id"] == "job-1"
    assert ("table", ("jobs",), {}) in fake_client.calls
    assert any(name == "insert" for name, _, _ in fake_client.calls)


# 4. Supabase unavailable -------------------------------------------------------------


def test_save_job_supabase_unavailable(monkeypatch):
    def raise_runtime_error():
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")

    monkeypatch.setattr(job_service, "get_supabase_client", raise_runtime_error)

    with pytest.raises(JobStorageError) as exc_info:
        job_service.save_job(make_job())

    assert exc_info.value.status_code == 503


# 5. Missing optional fields ----------------------------------------------------------


def test_save_job_with_missing_optional_fields(monkeypatch):
    job = make_job(salary=None, skills=None, qualification=None)
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "job-2", **job}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    result = job_service.save_job(job)

    assert result["id"] == "job-2"


# 6. Invalid job data -------------------------------------------------------------------


def test_save_job_rejects_missing_telegram_metadata():
    job = make_job(telegram_channel=None)
    with pytest.raises(JobStorageError) as exc_info:
        job_service.save_job(job)
    assert exc_info.value.status_code == 400


def test_save_job_rejects_invalid_apply_url():
    job = make_job(original_apply_url="not-a-url")
    with pytest.raises(JobStorageError) as exc_info:
        job_service.save_job(job)
    assert exc_info.value.status_code == 400


def test_save_job_does_not_confuse_original_and_final_url(monkeypatch):
    job = make_job(
        original_apply_url="https://aggregator.com/job/1",
        final_apply_url="https://acme.com/careers/1",
    )
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "job-3", **job}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    job_service.save_job(job)

    insert_calls = [call for call in fake_client.calls if call[0] == "insert"]
    inserted_row = insert_calls[0][1][0]
    assert inserted_row["original_apply_url"] == "https://aggregator.com/job/1"
    assert inserted_row["final_apply_url"] == "https://acme.com/careers/1"


# 9/10/11. list_jobs and filtering -----------------------------------------------------


def test_list_jobs_returns_data(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[make_job()]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    jobs = job_service.list_jobs()

    assert len(jobs) == 1


def test_list_jobs_filters_by_date(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    job_service.list_jobs(date="2026-09-15")

    gte_calls = [call for call in fake_client.calls if call[0] == "gte"]
    lt_calls = [call for call in fake_client.calls if call[0] == "lt"]
    assert gte_calls and gte_calls[0][1] == ("posted_at", "2026-09-15T00:00:00+00:00")
    assert lt_calls and lt_calls[0][1] == ("posted_at", "2026-09-16T00:00:00+00:00")


def test_list_jobs_rejects_invalid_date(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    with pytest.raises(JobStorageError) as exc_info:
        job_service.list_jobs(date="not-a-date")
    assert exc_info.value.status_code == 400


def test_list_jobs_filters_by_company(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    job_service.list_jobs(company="Acme")

    ilike_calls = [call for call in fake_client.calls if call[0] == "ilike"]
    assert ("company", "%Acme%") in [call[1] for call in ilike_calls]


def test_list_jobs_filters_by_location(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    job_service.list_jobs(location="Bangalore")

    ilike_calls = [call for call in fake_client.calls if call[0] == "ilike"]
    assert ("location", "%Bangalore%") in [call[1] for call in ilike_calls]


# delete_jobs_for_date ----------------------------------------------------------------------


def test_delete_jobs_for_date_returns_count(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "1"}, {"id": "2"}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    deleted = job_service.delete_jobs_for_date("2026-09-15")

    assert deleted == 2
    gte_calls = [call for call in fake_client.calls if call[0] == "gte"]
    lt_calls = [call for call in fake_client.calls if call[0] == "lt"]
    assert gte_calls and gte_calls[0][1] == ("posted_at", "2026-09-15T00:00:00+00:00")
    assert lt_calls and lt_calls[0][1] == ("posted_at", "2026-09-16T00:00:00+00:00")
    assert any(call[0] == "delete" for call in fake_client.calls)


def test_delete_jobs_for_date_rejects_invalid_date(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    with pytest.raises(JobStorageError) as exc_info:
        job_service.delete_jobs_for_date("not-a-date")
    assert exc_info.value.status_code == 400


def test_delete_jobs_for_date_with_no_matches_returns_zero(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    assert job_service.delete_jobs_for_date("2026-09-15") == 0


# 13. get_job -----------------------------------------------------------------------------


def test_get_job_found(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "job-1", **make_job()}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    job = job_service.get_job("job-1")

    assert job["id"] == "job-1"


def test_get_job_not_found(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    assert job_service.get_job("missing") is None


def test_get_job_invalid_id_returns_400_not_500(monkeypatch):
    from postgrest.exceptions import APIError

    malformed_uuid_error = APIError({"message": "invalid input syntax for type uuid", "code": "22P02"})
    fake_client = FakeSupabaseClient(malformed_uuid_error)
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    with pytest.raises(JobStorageError) as exc_info:
        job_service.get_job("not-a-uuid")
    assert exc_info.value.status_code == 400


# 14. save_job() itself performs no deduplication ---------------------------------------
# (Dedup is an orchestration-layer concern - see job_exists() below and
# message_service._save_jobs, which checks job_exists() before calling save_job().
# save_job() itself stays a pure insert with no dedup awareness.)


def test_save_job_itself_does_not_dedupe(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "job-x", **make_job()}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    job_service.save_job(make_job())
    job_service.save_job(make_job())

    insert_calls = [call for call in fake_client.calls if call[0] == "insert"]
    assert len(insert_calls) == 2


# job_exists() ----------------------------------------------------------------------------


def test_job_exists_true_when_found(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[{"id": "job-x"}]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    assert job_service.job_exists("testchannel", 42) is True

    eq_calls = [call for call in fake_client.calls if call[0] == "eq"]
    assert ("telegram_channel", "testchannel") in [call[1] for call in eq_calls]
    assert ("telegram_message_id", 42) in [call[1] for call in eq_calls]


def test_job_exists_false_when_not_found(monkeypatch):
    fake_client = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(job_service, "_get_client", lambda: fake_client)

    assert job_service.job_exists("testchannel", 42) is False
