from app.services import job_service, message_service
from app.services.job_service import JobStorageError


def make_job(message_id: int) -> dict:
    return {
        "company": "Acme Corp",
        "title": "Software Engineer",
        "telegram_message_id": message_id,
        "telegram_channel": "testchannel",
        "telegram_message_url": f"https://t.me/testchannel/{message_id}",
        "original_apply_url": "https://acme.com/apply",
        "final_apply_url": None,
        "posted_at": "2026-09-15T09:00:00+00:00",
    }


def stub_no_existing_jobs(monkeypatch):
    """Most tests aren't about dedup - stub job_exists to always say "new"."""
    monkeypatch.setattr(job_service, "job_exists", lambda channel, message_id: False)


# 2. Multiple jobs inserted in one fetch ------------------------------------------------


def test_save_jobs_saves_all_on_success(monkeypatch):
    stub_no_existing_jobs(monkeypatch)
    saved = []

    def fake_save_job(job):
        saved.append(job)
        return {"id": f"id-{job['telegram_message_id']}"}

    monkeypatch.setattr(job_service, "save_job", fake_save_job)

    jobs = [make_job(1), make_job(2), make_job(3)]
    jobs_saved, jobs_duplicate, errors = message_service._save_jobs(jobs)

    assert jobs_saved == 3
    assert jobs_duplicate == 0
    assert errors == []
    assert all(job["saved"] for job in jobs)
    assert jobs[0]["id"] == "id-1"


# 3. One job failing while others succeed -----------------------------------------------


def test_save_jobs_isolates_individual_failures(monkeypatch):
    stub_no_existing_jobs(monkeypatch)

    def fake_save_job(job):
        if job["telegram_message_id"] == 2:
            raise JobStorageError("insert failed", status_code=500)
        return {"id": f"id-{job['telegram_message_id']}"}

    monkeypatch.setattr(job_service, "save_job", fake_save_job)

    jobs = [make_job(1), make_job(2), make_job(3)]
    jobs_saved, jobs_duplicate, errors = message_service._save_jobs(jobs)

    assert jobs_saved == 2
    assert jobs_duplicate == 0
    assert len(errors) == 1
    assert errors[0]["telegram_message_id"] == 2
    assert jobs[0]["saved"] is True
    assert jobs[1]["saved"] is False
    assert jobs[2]["saved"] is True


def test_save_jobs_handles_empty_list():
    jobs_saved, jobs_duplicate, errors = message_service._save_jobs([])
    assert jobs_saved == 0
    assert jobs_duplicate == 0
    assert errors == []


# Deduplication ---------------------------------------------------------------------------


def test_save_jobs_skips_already_saved_messages(monkeypatch):
    def fake_job_exists(channel, message_id):
        return message_id == 2  # job 2 was already saved in a previous fetch

    monkeypatch.setattr(job_service, "job_exists", fake_job_exists)

    save_calls = []

    def fake_save_job(job):
        save_calls.append(job["telegram_message_id"])
        return {"id": f"id-{job['telegram_message_id']}"}

    monkeypatch.setattr(job_service, "save_job", fake_save_job)

    jobs = [make_job(1), make_job(2), make_job(3)]
    jobs_saved, jobs_duplicate, errors = message_service._save_jobs(jobs)

    assert jobs_saved == 2
    assert jobs_duplicate == 1
    assert errors == []
    assert save_calls == [1, 3]  # job 2 was never inserted
    assert jobs[1]["saved"] is False
    assert jobs[1]["duplicate"] is True


def test_save_jobs_falls_through_to_insert_if_existence_check_fails(monkeypatch):
    def fake_job_exists(channel, message_id):
        raise JobStorageError("Supabase hiccup", status_code=502)

    monkeypatch.setattr(job_service, "job_exists", fake_job_exists)

    def fake_save_job(job):
        return {"id": f"id-{job['telegram_message_id']}"}

    monkeypatch.setattr(job_service, "save_job", fake_save_job)

    jobs_saved, jobs_duplicate, errors = message_service._save_jobs([make_job(1)])

    assert jobs_saved == 1
    assert jobs_duplicate == 0
