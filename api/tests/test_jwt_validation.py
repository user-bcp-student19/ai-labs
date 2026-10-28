import base64
import json
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.main import create_app, legacy_identity
from jwt_support import PRIVATE_PEM, sign_token


def bearer(value: str) -> str:
    return "Bearer " + value


def headers_for(value: str) -> dict[str, str]:
    return {"Authorization": bearer(value)}


def encode_segment(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def valid_claims(**overrides: object) -> dict:
    now = int(time.time())
    claims = {
        "sub": "student",
        "role": "STUDENT",
        "iss": main.AUTH_TOKEN_ISSUER,
        "aud": main.AUTH_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return claims


def test_accepts_valid_signed_token_on_protected_endpoint(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers_for(sign_token()))

    assert response.status_code == 200


def test_rejects_token_with_tampered_payload(tmp_path: Path) -> None:
    header, _, signature = sign_token(role="STUDENT").split(".")
    forged_payload = encode_segment(valid_claims(role="TRAINER"))
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers=headers_for(f"{header}.{forged_payload}.{signature}"),
        )

    assert response.status_code == 401


def test_rejects_token_signed_with_another_key() -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    with pytest.raises(HTTPException) as error:
        legacy_identity(bearer(sign_token(key=other_pem)))

    assert error.value.status_code == 401


def test_rejects_unsigned_token() -> None:
    unsigned = jwt.encode(valid_claims(), None, algorithm="none")

    with pytest.raises(HTTPException) as error:
        legacy_identity(bearer(unsigned))

    assert error.value.status_code == 401


@pytest.mark.parametrize("claims_override", [{"iss": "otro-emisor"}, {"aud": "otra-audiencia"}])
def test_rejects_wrong_issuer_or_audience(claims_override: dict) -> None:
    token_value = jwt.encode(valid_claims(**claims_override), PRIVATE_PEM, algorithm="RS256")

    with pytest.raises(HTTPException) as error:
        legacy_identity(bearer(token_value))

    assert error.value.status_code == 401


@pytest.mark.parametrize("missing_claim", ["iss", "aud", "exp", "sub", "role"])
def test_rejects_token_missing_required_claim(missing_claim: str) -> None:
    claims = valid_claims()
    claims.pop(missing_claim)
    token_value = jwt.encode(claims, PRIVATE_PEM, algorithm="RS256")

    with pytest.raises(HTTPException) as error:
        legacy_identity(bearer(token_value))

    assert error.value.status_code == 401


def test_rejects_when_verification_key_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(main.AUTH_PUBLIC_KEY_PATH_ENV)
    main.token_verification_key.cache_clear()

    with pytest.raises(HTTPException) as error:
        legacy_identity(bearer(sign_token()))

    assert error.value.status_code == 401


def test_legacy_shared_secret_is_not_in_application_source() -> None:
    source = Path(main.__file__).read_text(encoding="utf-8")

    assert "WORKSHOP_SECRET_2026" not in source
