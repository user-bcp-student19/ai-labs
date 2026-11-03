"""H-API-02: caracterización del contrato de tareas y pruebas de SQL parametrizado."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import auth_headers

TASK_KEYS = {"id", "title", "description", "status", "owner", "priority", "createdAt"}
SUMMARY_KEYS = {"owner", "total", "byStatus", "highPriorityOpen"}
INJECTION_LITERAL = "' OR '1'='1"
DROP_TABLE_LITERAL = "x'); DROP TABLE tasks;--"


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_lists_seeded_tasks_with_contract_keys(client) -> None:
    response = client.get("/api/tasks", headers=auth_headers())
    tasks = response.json()
    assert response.status_code == 200
    assert [task["title"] for task in tasks] == ["Refactor login", "Review API"]
    assert all(set(task) == TASK_KEYS for task in tasks)
    assert all(task["owner"] == "student" for task in tasks)


def test_trainer_sees_only_own_tasks(client) -> None:
    response = client.get("/api/tasks", headers=auth_headers("trainer", "TRAINER"))
    assert [task["title"] for task in response.json()] == ["Trainer notes"]


def test_create_task_applies_defaults(client) -> None:
    response = client.post("/api/tasks", headers=auth_headers(), json={"title": "Only title"})
    body = response.json()
    assert response.status_code == 201
    assert set(body) == TASK_KEYS
    assert (body["description"], body["status"], body["priority"], body["owner"]) == ("", "TODO", "MEDIUM", "student")


def test_summary_counts_seeded_tasks(client) -> None:
    response = client.get("/api/summary", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_summary_ignores_done_and_archived_as_open(client) -> None:
    for status in ("DONE", "ARCHIVED", "TODO"):
        client.post("/api/tasks", headers=auth_headers(), json={"title": status, "status": status, "priority": "HIGH"})
    summary = client.get("/api/summary", headers=auth_headers()).json()
    assert summary["total"] == 5
    assert summary["highPriorityOpen"] == 2
    assert set(summary) == SUMMARY_KEYS


def test_task_with_apostrophe_is_stored_literally(client) -> None:
    created = client.post("/api/tasks", headers=auth_headers(), json={"title": "O'Brien", "description": "it's"})
    assert created.status_code == 201
    assert created.json()["title"] == "O'Brien"
    titles = [task["title"] for task in client.get("/api/tasks", headers=auth_headers()).json()]
    assert "O'Brien" in titles


def test_sql_in_task_fields_is_stored_literally_and_table_survives(client) -> None:
    created = client.post("/api/tasks", headers=auth_headers(), json={"title": DROP_TABLE_LITERAL})
    assert created.status_code == 201
    assert created.json()["title"] == DROP_TABLE_LITERAL
    assert len(client.get("/api/tasks", headers=auth_headers()).json()) == 3


@pytest.mark.parametrize("path", ["/api/tasks", "/api/summary"])
def test_owner_filter_is_not_injectable(client, path: str) -> None:
    response = client.get(path, headers=auth_headers(), params={"owner": INJECTION_LITERAL})
    assert response.status_code in (200, 403)
    if response.status_code == 200:
        body = response.json()
        assert body == [] or body["total"] == 0
