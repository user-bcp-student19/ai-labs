import base64
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.main import create_app, legacy_identity


def token(username: str = "student", role: str = "STUDENT") -> str:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_legacy_token_resolves_username_and_role() -> None:
    assert legacy_identity(f"Bearer {token('student', 'STUDENT')}") == {
        "username": "student",
        "role": "STUDENT",
    }


def test_legacy_token_rejects_expired_token() -> None:
    expired_payload = f"student|STUDENT|{int(time.time()) - 1}|WORKSHOP_SECRET_2026"
    expired_token = base64.b64encode(expired_payload.encode()).decode()

    with pytest.raises(HTTPException) as error:
        legacy_identity(f"Bearer {expired_token}")

    assert error.value.status_code == 401


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_characterizes_owner_filter_with_regular_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", params={"owner": "student"}, headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(task["owner"] == "student" for task in response.json())


def test_filters_owner_sql_expression_as_literal_value(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    injected_owner = "student' OR '1'='1"
    with TestClient(app) as client:
        tasks = client.get(
            "/api/tasks",
            params={"owner": injected_owner},
            headers=headers(),
        )
        summary = client.get(
            "/api/summary",
            params={"owner": injected_owner},
            headers=headers(),
        )

    assert tasks.status_code == 200
    assert tasks.json() == []
    assert summary.status_code == 200
    assert summary.json()["total"] == 0


def test_creates_task_with_quoted_fields(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": "Manager's notes",
                "description": "User's acceptance criteria",
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Manager's notes"
    assert response.json()["description"] == "User's acceptance criteria"


def test_rejects_student_reading_trainer_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            params={"owner": "trainer"},
            headers=headers(username="student"),
        )

    assert response.status_code == 200
    assert all(task["owner"] == "student" for task in response.json())


def test_lists_empty_result_for_unknown_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            params={"owner": "unknown"},
            headers=headers(),
        )

    assert response.status_code == 200
    assert response.json() == []


def test_creates_task_with_empty_object_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_rejects_non_object_task_body(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json=[])

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_returns_internal_error_when_task_table_is_missing(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DROP TABLE tasks")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_returns_internal_error_when_task_creation_fails(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DROP TABLE tasks")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_returns_empty_summary_for_unknown_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/summary",
            params={"owner": "unknown"},
            headers=headers(),
        )

    assert response.status_code == 200
    assert response.json() == {
        "owner": "unknown",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_returns_summary_for_seeded_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/summary",
            params={"owner": "student"},
            headers=headers(),
        )

    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_returns_internal_error_when_summary_query_fails(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DROP TABLE tasks")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/summary", headers=headers())

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_rejects_upload_without_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"content", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid upload"}


def test_rejects_upload_when_file_part_is_missing(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_returns_internal_error_when_upload_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def fail_write(self: Path, content: bytes) -> int:
        raise OSError("simulated filesystem failure")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"content", "text/plain")},
        )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_returns_backend_health_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    upstream_response = SimpleNamespace(status=200, data=b'{"status":"UP"}')
    monkeypatch.setattr(
        main.urllib3,
        "PoolManager",
        lambda: SimpleNamespace(
            request=lambda *args, **kwargs: upstream_response,
        ),
    )
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"status":"UP"}',
    }


def test_backend_health_returns_zero_status_when_upstream_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def fail_request(*args: object, **kwargs: object) -> None:
        raise TimeoutError("upstream timed out")

    monkeypatch.setattr(
        main.urllib3,
        "PoolManager",
        lambda: SimpleNamespace(request=fail_request),
    )
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "upstream timed out",
    }


def test_returns_internal_error_when_backend_health_configuration_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def fail_configuration_lookup(name: str, default: str | None = None) -> str:
        raise OSError("simulated configuration failure")

    monkeypatch.setattr(main.os, "getenv", fail_configuration_lookup)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", "/api/tasks", {}),
        ("POST", "/api/tasks", {"json": {}}),
        ("GET", "/api/summary", {}),
        ("POST", "/api/requirements", {}),
        ("GET", "/api/backend-health", {}),
    ],
)
def test_all_endpoints_require_valid_authentication(
    tmp_path: Path,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.request(method, path, **kwargs)

    assert response.status_code == 401
    assert response.json()["detail"].startswith("Invalid token:")


def test_trainer_lists_own_tasks_by_default(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers=headers(username="trainer", role="TRAINER"),
        )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert all(task["owner"] == "trainer" for task in response.json())


def test_characterizes_student_creating_trainer_task(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": "Observed cross-owner task",
                "description": "Characterization only",
                "owner": "trainer",
            },
        )

    assert response.status_code == 201
    assert response.json()["owner"] == "trainer"


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    content = b"Login must be accessible"
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": str(upload_dir / "requirements.txt"),
        "size": len(content),
    }
    assert (upload_dir / "requirements.txt").read_bytes() == content


def test_accepts_upload_at_maximum_size(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    content = b"x" * (4 * 1024 * 1024)
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )

    assert response.status_code == 201
    assert response.json()["size"] == 4 * 1024 * 1024
    assert (upload_dir / "requirements.txt").stat().st_size == len(content)


def test_rejects_upload_filename_with_path_separators(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("../outside.txt", b"outside", "text/plain")},
        )

    assert response.status_code == 400
    assert not (tmp_path / "outside.txt").exists()
    assert not (upload_dir / "outside.txt").exists()


def test_rejects_upload_without_filename(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("", b"content", "text/plain")},
        )

    assert response.status_code == 422
    assert not list(upload_dir.iterdir())


def test_rejects_unapproved_upload_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("notes.pdf", b"not a requirement text file", "application/pdf")},
        )

    assert response.status_code == 400
    assert not (upload_dir / "notes.pdf").exists()


def test_rejects_upload_above_maximum_size(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    content = b"x" * (4 * 1024 * 1024 + 1)
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("large.txt", content, "text/plain")},
        )

    assert response.status_code == 400
    assert not (upload_dir / "large.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
