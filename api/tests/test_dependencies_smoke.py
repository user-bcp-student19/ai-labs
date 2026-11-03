"""Caracterización de H-API-05: rutas que usan urllib3 y python-multipart."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import auth_headers


class FakeResponse:
    status = 200
    data = b'{"status":"UP"}'


class FakePoolManager:
    def request(self, method: str, url: str, timeout: float) -> FakeResponse:
        return FakeResponse()


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as test_client:
        yield test_client


def test_backend_health_keeps_response_shape(client, monkeypatch) -> None:
    monkeypatch.setattr("app.main.urllib3.PoolManager", FakePoolManager)
    response = client.get("/api/backend-health", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": '{"status":"UP"}'}


def test_upload_keeps_response_shape(client, tmp_path: Path) -> None:
    content = b"Login must be accessible"
    response = client.post(
        "/api/requirements",
        headers=auth_headers(),
        files={"file": ("requirements.txt", content, "text/plain")},
    )
    body = response.json()
    assert response.status_code == 201
    assert set(body) == {"owner", "fileName", "storedAt", "size"}
    assert body["owner"] == "student"
    assert body["fileName"] == "requirements.txt"
    assert body["size"] == len(content)
    assert (tmp_path / "uploads" / "requirements.txt").read_bytes() == content
