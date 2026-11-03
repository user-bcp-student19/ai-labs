"""H-API-04: carga segura de archivos (nombre, extensión, tamaño y ubicación)."""
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_BYTES
from app.main import create_app
from app.uploads import resolve_target
from tests.helpers import auth_headers

UPLOAD_URL = "/api/requirements"


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def client(tmp_path: Path, upload_dir: Path):
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as test_client:
        yield test_client


def upload(client, filename: str, content: bytes = b"content"):
    return client.post(UPLOAD_URL, headers=auth_headers(), files={"file": (filename, content, "text/plain")})


def test_valid_upload_keeps_contract_and_stored_path_shape(client, upload_dir: Path) -> None:
    response = upload(client, "requirements.txt", b"abc")
    body = response.json()
    assert response.status_code == 201
    assert body == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": str(upload_dir / "requirements.txt"),
        "size": 3,
    }
    assert (upload_dir / "requirements.txt").read_bytes() == b"abc"


@pytest.mark.parametrize("extension", sorted(ALLOWED_UPLOAD_EXTENSIONS))
def test_allowed_extensions_are_accepted(client, extension: str) -> None:
    assert upload(client, "spec" + extension).status_code == 201


def test_uppercase_extension_is_accepted(client) -> None:
    assert upload(client, "SPEC.TXT").status_code == 201


@pytest.mark.parametrize("filename", ["../evil.txt", "..\\evil.txt", "/tmp/evil.txt", "a/b/evil.txt"])
def test_path_components_are_stripped(client, tmp_path: Path, upload_dir: Path, filename: str) -> None:
    response = upload(client, filename)
    assert response.status_code == 201
    assert response.json()["fileName"] == "evil.txt"
    assert (upload_dir / "evil.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_unsafe_characters_are_replaced(client, upload_dir: Path) -> None:
    response = upload(client, "my spec;rm -rf.txt")
    assert response.status_code == 201
    assert response.json()["fileName"] == "my_spec_rm_-rf.txt"
    assert (upload_dir / "my_spec_rm_-rf.txt").exists()


@pytest.mark.parametrize("filename", ["...", "..", "."])
def test_names_without_content_are_rejected(client, filename: str) -> None:
    assert upload(client, filename).status_code == 400


@pytest.mark.parametrize("filename", ["malware.exe", "page.html", "README", ".txt"])
def test_disallowed_extensions_are_rejected(client, upload_dir: Path, filename: str) -> None:
    response = upload(client, filename)
    assert response.status_code == 415
    assert not any(upload_dir.iterdir())


def test_file_at_limit_is_accepted(client) -> None:
    response = upload(client, "limit.txt", b"x" * MAX_UPLOAD_BYTES)
    assert response.status_code == 201
    assert response.json()["size"] == MAX_UPLOAD_BYTES


def test_file_over_limit_is_rejected_and_not_kept(client, upload_dir: Path) -> None:
    response = upload(client, "big.txt", b"x" * (MAX_UPLOAD_BYTES + 1))
    assert response.status_code == 413
    assert not (upload_dir / "big.txt").exists()


def test_resolve_target_rejects_paths_outside_upload_dir(tmp_path: Path) -> None:
    with pytest.raises(HTTPException) as error:
        resolve_target(tmp_path / "uploads", "../escape.txt")
    assert error.value.status_code == 400
