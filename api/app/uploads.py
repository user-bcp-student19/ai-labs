import re
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile

from app.config import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_BYTES, UPLOAD_CHUNK_BYTES

UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")
INVALID_FILENAME_DETAIL = "Invalid file name"
UNSUPPORTED_EXTENSION_DETAIL = "Unsupported file type"
FILE_TOO_LARGE_DETAIL = "File too large"
BAD_REQUEST_STATUS_CODE = 400
FILE_TOO_LARGE_STATUS_CODE = 413
UNSUPPORTED_MEDIA_TYPE_STATUS_CODE = 415


def sanitize_filename(raw_name: str | None) -> str:
    base_name = PurePosixPath((raw_name or "").replace("\\", "/")).name
    safe_name = UNSAFE_FILENAME_CHARACTERS.sub("_", base_name)
    if not safe_name.strip("."):
        raise HTTPException(status_code=BAD_REQUEST_STATUS_CODE, detail=INVALID_FILENAME_DETAIL)
    return safe_name


def validate_extension(file_name: str) -> None:
    if PurePosixPath(file_name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=UNSUPPORTED_MEDIA_TYPE_STATUS_CODE, detail=UNSUPPORTED_EXTENSION_DETAIL)


def resolve_target(upload_dir: Path, file_name: str) -> Path:
    target = upload_dir / file_name
    if not target.resolve().is_relative_to(upload_dir.resolve()):
        raise HTTPException(status_code=BAD_REQUEST_STATUS_CODE, detail=INVALID_FILENAME_DETAIL)
    return target


async def save_limited(upload: UploadFile, target: Path) -> int:
    written = 0
    try:
        with target.open("wb") as destination:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=FILE_TOO_LARGE_STATUS_CODE, detail=FILE_TOO_LARGE_DETAIL)
                destination.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    return written
