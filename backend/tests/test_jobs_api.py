from fastapi.testclient import TestClient

from app.main import app
from app.services import job_service

client = TestClient(app)


def make_job(job_id: str) -> dict:
    return {
        "id": job_id,
        "company": "Acme Corp",
        "title": "Software Engineer",
        "location": "Bangalore",
        "posted_at": "2026-09-15T09:00:00+00:00",
    }


# 9. GET /api/jobs ------------------------------------------------------------------------


def test_list_jobs_endpoint(monkeypatch):
    monkeypatch.setattr(job_service, "list_jobs", lambda **kwargs: [make_job("1"), make_job("2")])

    response = client.get("/api/jobs")

    assert response.status_code == 200
    assert len(response.json()) == 2


# 10/11/12. filters are forwarded ----------------------------------------------------------


def test_list_jobs_endpoint_forwards_filters(monkeypatch):
    captured = {}

    def fake_list_jobs(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(job_service, "list_jobs", fake_list_jobs)

    client.get("/api/jobs?date=2026-09-15&company=Acme&location=Bangalore&limit=10&offset=5")

    assert captured["date"] == "2026-09-15"
    assert captured["company"] == "Acme"
    assert captured["location"] == "Bangalore"
    assert captured["limit"] == 10
    assert captured["offset"] == 5


# 13. GET /api/jobs/{id} --------------------------------------------------------------------


def test_get_job_endpoint_found(monkeypatch):
    monkeypatch.setattr(job_service, "get_job", lambda job_id: make_job(job_id))

    response = client.get("/api/jobs/abc-123")

    assert response.status_code == 200
    assert response.json()["id"] == "abc-123"


def test_get_job_endpoint_not_found(monkeypatch):
    monkeypatch.setattr(job_service, "get_job", lambda job_id: None)

    response = client.get("/api/jobs/missing")

    assert response.status_code == 404
