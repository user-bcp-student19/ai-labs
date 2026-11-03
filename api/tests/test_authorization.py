"""H-API-03: la autorización por propietario depende solo de la identidad."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import auth_headers

FOREIGN_OWNER = "trainer"
OWN_TASK_COUNT = 2


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as test_client:
        yield test_client


def test_explicit_own_owner_keeps_working(client) -> None:
    tasks = client.get("/api/tasks", headers=auth_headers(), params={"owner": "student"})
    summary = client.get("/api/summary", headers=auth_headers(), params={"owner": "student"})
    created = client.post("/api/tasks", headers=auth_headers(), json={"title": "Mine", "owner": "student"})
    assert tasks.status_code == 200 and len(tasks.json()) == OWN_TASK_COUNT
    assert summary.status_code == 200 and summary.json()["owner"] == "student"
    assert created.status_code == 201 and created.json()["owner"] == "student"


def test_empty_owner_param_falls_back_to_identity(client) -> None:
    response = client.get("/api/tasks", headers=auth_headers(), params={"owner": ""})
    assert response.status_code == 200
    assert len(response.json()) == OWN_TASK_COUNT


@pytest.mark.parametrize("path", ["/api/tasks", "/api/summary"])
def test_foreign_owner_is_forbidden_on_reads(client, path: str) -> None:
    response = client.get(path, headers=auth_headers(), params={"owner": FOREIGN_OWNER})
    assert response.status_code == 403


def test_foreign_owner_is_forbidden_on_create_and_nothing_is_inserted(client) -> None:
    response = client.post("/api/tasks", headers=auth_headers(), json={"title": "Spoofed", "owner": FOREIGN_OWNER})
    trainer_tasks = client.get("/api/tasks", headers=auth_headers(FOREIGN_OWNER, "TRAINER")).json()
    assert response.status_code == 403
    assert [task["title"] for task in trainer_tasks] == ["Trainer notes"]


def test_forbidden_detail_is_generic(client) -> None:
    response = client.get("/api/tasks", headers=auth_headers(), params={"owner": FOREIGN_OWNER})
    assert response.json() == {"detail": "Forbidden"}
