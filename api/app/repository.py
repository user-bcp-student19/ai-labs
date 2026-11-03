import sqlite3

from app.schemas import TaskCreate, TaskResponse

TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"
CREATE_TASKS_TABLE = (
    "CREATE TABLE IF NOT EXISTS tasks ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, "
    "status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)"
)
INSERT_TASK = (
    "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
    "VALUES (?,?,?,?,?,datetime('now'))"
)
SEED_TASKS = (
    ("Refactor login", "Separar responsabilidades en frontend", "TODO", "student", "HIGH"),
    ("Review API", "Revisar seguridad de endpoints", "IN_PROGRESS", "student", "MEDIUM"),
    ("Trainer notes", "Preparar retrospectiva", "TODO", "trainer", "LOW"),
)


def row_to_task(row: sqlite3.Row) -> TaskResponse:
    return TaskResponse(**{column: row[column] for column in row.keys()})


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def ensure_schema_with_seed(self) -> None:
        self._connection.execute(CREATE_TASKS_TABLE)
        total = self._connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
        if total == 0:
            self._connection.executemany(INSERT_TASK, SEED_TASKS)
            self._connection.commit()

    def list_by_owner(self, owner: str) -> list[TaskResponse]:
        rows = self._connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner=? ORDER BY id", (owner,)
        ).fetchall()
        return [row_to_task(row) for row in rows]

    def create(self, task: TaskCreate, owner: str) -> TaskResponse:
        cursor = self._connection.execute(
            INSERT_TASK, (task.title, task.description, task.status, owner, task.priority)
        )
        self._connection.commit()
        row = self._connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
        return row_to_task(row)
