from __future__ import annotations

import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

import urllib3
from fastapi import Depends, FastAPI, File, Header, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import AuthSettings, CLOSED_TASK_STATUSES, HIGH_PRIORITY
from app.repository import TaskRepository
from app.schemas import TaskCreate, TaskResponse, TaskSummary, UploadResponse
from app.security import authenticate_bearer, resolve_owner
from app.uploads import resolve_target, sanitize_filename, save_limited, validate_extension

def summarize_tasks(owner: str, tasks: list[TaskResponse]) -> TaskSummary:
    by_status = Counter(task.status for task in tasks)
    high_priority_open = sum(
        1 for task in tasks if task.priority == HIGH_PRIORITY and task.status not in CLOSED_TASK_STATUSES
    )
    return TaskSummary(owner=owner, total=len(tasks), byStatus=dict(by_status), highPriorityOpen=high_priority_open)


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    auth_settings = AuthSettings.from_environment()
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    tasks = TaskRepository(connection)
    tasks.ensure_schema_with_seed()

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def current_identity(authorization: str = Header(default="")) -> dict[str, str]:
        return authenticate_bearer(authorization, auth_settings).model_dump()

    @app.get("/api/tasks", response_model=list[TaskResponse], response_model_by_alias=True)
    def list_tasks(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(current_identity)) -> list[TaskResponse]:
        return tasks.list_by_owner(resolve_owner(identity, owner))

    @app.post("/api/tasks", status_code=201, response_model=TaskResponse, response_model_by_alias=True)
    def create_task(payload: TaskCreate, identity: dict[str, str] = Depends(current_identity)) -> TaskResponse:
        return tasks.create(payload, resolve_owner(identity, payload.owner))

    @app.get("/api/summary", response_model=TaskSummary)
    def summary(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(current_identity)) -> TaskSummary:
        resolved_owner = resolve_owner(identity, owner)
        return summarize_tasks(resolved_owner, tasks.list_by_owner(resolved_owner))

    @app.post("/api/requirements", status_code=201, response_model=UploadResponse)
    async def upload_requirement(file: UploadFile = File(...), identity: dict[str, str] = Depends(current_identity)) -> UploadResponse:
        file_name = sanitize_filename(file.filename)
        validate_extension(file_name)
        target = resolve_target(Path(selected_uploads), file_name)
        size = await save_limited(file, target)
        return UploadResponse(owner=identity["username"], fileName=file_name, storedAt=str(target), size=size)

    @app.get("/api/backend-health")
    def backend_health(identity: dict[str, str] = Depends(current_identity)) -> dict[str, Any]:
        url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
        try:
            response = urllib3.PoolManager().request("GET", url, timeout=3.0)
            return {"requestedBy": identity["username"], "status": response.status, "body": response.data.decode("utf-8")}
        except Exception as error:
            return {"requestedBy": identity["username"], "status": 0, "body": str(error)}

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
