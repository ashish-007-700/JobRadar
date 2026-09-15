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


# 2. Multiple jobs inserted in one fetch ------------------------------------------------


def test_save_jobs_saves_all_on_success(monkeypatch):
    saved = []

    def fake_save_job(job):
        saved.append(job)
        return {"id": f"id-{job['telegram_message_id']}"}

    monkeypatch.setattr(job_service, "save_job", fake_save_job)

    jobs = [make_job(1), make_job(2), make_job(3)]
    jobs_saved, errors = message_service._save_jobs(jobs)

    assert jobs_saved == 3
    assert errors == []
    assert all(job["saved"] for job in jobs)
    assert jobs[0]["id"] == "id-1"


# 3. One job failing while others succeed -----------------------------------------------


def test_save_jobs_isolates_individual_failures(monkeypatch):
    def fake_save_job(job):
        if job["telegram_message_id"] == 2:
            raise JobStorageError("insert failed", status_code=500)
        return {"id": f"id-{job['telegram_message_id']}"}

    monkeypatch.setattr(job_service, "save_job", fake_save_job)

    jobs = [make_job(1), make_job(2), make_job(3)]
    jobs_saved, errors = message_service._save_jobs(jobs)

    assert jobs_saved == 2
    assert len(errors) == 1
    assert errors[0]["telegram_message_id"] == 2
    assert jobs[0]["saved"] is True
    assert jobs[1]["saved"] is False
    assert jobs[2]["saved"] is True


def test_save_jobs_handles_empty_list():
    jobs_saved, errors = message_service._save_jobs([])
    assert jobs_saved == 0
    assert errors == []
