import os

from pydantic import BaseModel, Field, SecretStr

JWT_ALGORITHM = "HS256"
JWT_ENVIRONMENT_VARIABLES = ("JWT_SECRET", "JWT_ISSUER", "JWT_AUDIENCE")
DEFAULT_TASK_STATUS = "TODO"
DEFAULT_TASK_PRIORITY = "MEDIUM"
HIGH_PRIORITY = "HIGH"
CLOSED_TASK_STATUSES = frozenset({"DONE", "ARCHIVED"})
ALLOWED_UPLOAD_EXTENSIONS = frozenset({".txt", ".md", ".pdf", ".docx"})
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 64 * 1024


class AuthSettings(BaseModel):
    jwt_secret: SecretStr = Field(min_length=1)
    jwt_issuer: str = Field(min_length=1)
    jwt_audience: str = Field(min_length=1)

    @classmethod
    def from_environment(cls) -> "AuthSettings":
        missing = [name for name in JWT_ENVIRONMENT_VARIABLES if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                f"Missing required authentication environment variables: {', '.join(missing)}"
            )
        return cls(
            jwt_secret=os.environ["JWT_SECRET"],
            jwt_issuer=os.environ["JWT_ISSUER"],
            jwt_audience=os.environ["JWT_AUDIENCE"],
        )
