"""Contract error and edge cases for the documented API endpoints."""
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import auth_headers

TASK_PAYLOAD = {
    "title": "Review API",
    "description": "Check required changes",
    "status": "TODO",
    "priority": "HIGH",
}
UPLOAD_FILE = {"file": ("requirements.txt", b"Login requirement", "text/plain")}
ERROR_BODY = "Internal Server Error"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "request_options"),
    [
        ("GET", "/api/tasks", {}),
        ("POST", "/api/tasks", {"json": TASK_PAYLOAD}),
        ("GET", "/api/summary", {}),
        ("POST", "/api/requirements", {"files": UPLOAD_FILE}),
        ("GET", "/api/backend-health", {}),
    ],
)
def test_each_endpoint_rejects_missing_authentication(
    client: TestClient,
    method: str,
    path: str,
    request_options: dict[str, object],
) -> None:
    response = client.request(method, path, **request_options)
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("DELETE", "/api/tasks"),
        ("PUT", "/api/summary"),
        ("PUT", "/api/requirements"),
        ("PUT", "/api/backend-health"),
    ],
)
def test_each_endpoint_rejects_unsupported_method(
    client: TestClient,
    method: str,
    path: str,
) -> None:
    response = client.request(method, path, headers=auth_headers())
    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


@pytest.mark.parametrize("path", ["/api/tasks", "/api/summary"])
def test_read_endpoints_reject_a_different_owner(
    client: TestClient,
    path: str,
) -> None:
    response = client.get(path, headers=auth_headers(), params={"owner": "trainer"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_create_task_rejects_a_different_owner(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        json={**TASK_PAYLOAD, "owner": "trainer"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_create_task_accepts_an_empty_object_and_applies_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth_headers(), json={})
    body = response.json()
    assert response.status_code == 201
    assert body == {
        "id": 4,
        "title": "",
        "description": "",
        "status": "TODO",
        "owner": "student",
        "priority": "MEDIUM",
        "createdAt": body["createdAt"],
    }
    datetime.strptime(body["createdAt"], "%Y-%m-%d %H:%M:%S")


def test_create_task_rejects_a_non_string_title(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        json={**TASK_PAYLOAD, "title": 5},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "title"]


def test_summary_uses_identity_for_empty_owner_filter(client: TestClient) -> None:
    response = client.get(
        "/api/summary",
        headers=auth_headers(),
        params={"owner": ""},
    )
    assert response.status_code == 200
    assert response.json()["owner"] == "student"
    assert response.json()["total"] == 2


def test_upload_rejects_missing_file(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=auth_headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_rejects_multipart_without_boundary(client: TestClient) -> None:
    response = client.post(
        "/api/requirements",
        headers={
            **auth_headers(),
            "Content-Type": "multipart/form-data",
        },
        content="not a multipart body",
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing boundary in multipart."}


@pytest.mark.parametrize(
    ("path", "method", "kwargs"),
    [
        ("/api/tasks", "GET", {}),
        ("/api/summary", "GET", {}),
    ],
)
def test_task_read_endpoints_return_generic_500_on_database_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    method: str,
    kwargs: dict[str, object],
) -> None:
    def fail_read(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr("app.main.TaskRepository.list_by_owner", fail_read)
    response = client.request(method, path, headers=auth_headers(), **kwargs)
    assert response.status_code == 500
    assert response.text == ERROR_BODY


def test_create_task_returns_generic_500_on_database_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr("app.main.TaskRepository.create", fail_create)
    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        json=TASK_PAYLOAD,
    )
    assert response.status_code == 500
    assert response.text == ERROR_BODY


def test_upload_returns_generic_500_on_filesystem_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_save(*args: object, **kwargs: object) -> int:
        raise OSError("filesystem unavailable")

    monkeypatch.setattr("app.main.save_limited", fail_save)
    response = client.post(
        "/api/requirements",
        headers=auth_headers(),
        files=UPLOAD_FILE,
    )
    assert response.status_code == 500
    assert response.text == ERROR_BODY


@pytest.mark.parametrize(
    ("upstream_status", "upstream_body"),
    [
        (503, b'{"status":"DOWN"}'),
        (0, b"upstream unavailable"),
    ],
)
def test_backend_health_keeps_api_200_for_upstream_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    upstream_status: int,
    upstream_body: bytes,
) -> None:
    class FakeResponse:
        status = upstream_status
        data = upstream_body

    class FakePoolManager:
        def request(self, method: str, url: str, timeout: float) -> FakeResponse:
            if upstream_status == 0:
                raise RuntimeError(upstream_body.decode("utf-8"))
            return FakeResponse()

    monkeypatch.setattr("app.main.urllib3.PoolManager", FakePoolManager)
    response = client.get("/api/backend-health", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": upstream_status,
        "body": upstream_body.decode("utf-8"),
    }
