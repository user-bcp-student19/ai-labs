import base64
import time
from collections.abc import Iterator
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import JWT_ALGORITHM, JWT_ENVIRONMENT_VARIABLES
from app.main import create_app
from tests.helpers import TEST_JWT_SECRET, auth_headers, make_token


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as test_client:
        yield test_client


def test_valid_token_preserves_identity_and_route_contract(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth_headers())

    assert response.status_code == 200
    assert all(task["owner"] == "student" for task in response.json())


def test_role_claim_does_not_change_existing_task_access(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth_headers(role="TRAINER"))

    assert response.status_code == 200


@pytest.mark.parametrize(
    "authorization",
    ["not-a-token", "Basic value", "Bearer", "Bearer "],
)
def test_rejects_invalid_bearer_header(client: TestClient, authorization: str) -> None:
    response = client.get("/api/tasks", headers={"Authorization": authorization})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        make_token(signing_key="different-test-only-key-with-adequate-length"),
        make_token(expires_at=int(time.time()) - 1),
        make_token(issuer="unexpected-test-issuer"),
        make_token(audience="unexpected-test-audience"),
    ],
)
def test_rejects_invalid_token_signature_or_registered_claims(
    client: TestClient,
    token: str,
) -> None:
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


@pytest.mark.parametrize("claim", ["exp", "iss", "aud", "sub", "role"])
def test_rejects_token_missing_required_claim(client: TestClient, claim: str) -> None:
    token = make_token(omit_claims=(claim,))
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_rejects_unsigned_token(client: TestClient) -> None:
    claims = {
        "sub": "student",
        "role": "STUDENT",
        "exp": int(time.time()) + 3600,
        "iss": "ai-labs-tests",
        "aud": "ai-labs-api-tests",
    }
    token = jwt.encode(claims, key="", algorithm="none")
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_rejects_non_string_identity_claims(client: TestClient) -> None:
    claims = {
        "sub": "student",
        "role": 123,
        "exp": int(time.time()) + 3600,
        "iss": "ai-labs-tests",
        "aud": "ai-labs-api-tests",
    }
    token = jwt.encode(claims, key=TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_rejects_legacy_base64_token(client: TestClient) -> None:
    legacy_payload = f"student|STUDENT|{int(time.time()) + 3600}|legacy-test-placeholder"
    token = base64.b64encode(legacy_payload.encode()).decode()
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_create_app_requires_authentication_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for variable in JWT_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET, JWT_ISSUER, JWT_AUDIENCE"):
        create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))


def test_helper_tokens_use_fixed_allowed_algorithm() -> None:
    token = make_token()

    assert jwt.get_unverified_header(token)["alg"] == JWT_ALGORITHM
