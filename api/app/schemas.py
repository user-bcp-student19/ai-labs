from pydantic import BaseModel, Field

from app.config import DEFAULT_TASK_PRIORITY, DEFAULT_TASK_STATUS


class TaskCreate(BaseModel):
    title: str = ""
    description: str = ""
    status: str = DEFAULT_TASK_STATUS
    priority: str = DEFAULT_TASK_PRIORITY
    owner: str | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(serialization_alias="createdAt")


class UploadResponse(BaseModel):
    owner: str
    fileName: str
    storedAt: str
    size: int


class TaskSummary(BaseModel):
    owner: str
    total: int
    byStatus: dict[str, int]
    highPriorityOpen: int
