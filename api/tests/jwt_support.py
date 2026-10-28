import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app import main

TEST_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = TEST_KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
PUBLIC_PEM = TEST_KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def sign_token(
    username: str = "student",
    role: str = "STUDENT",
    expires_at: int | None = None,
    issuer: str = main.AUTH_TOKEN_ISSUER,
    audience: str = main.AUTH_TOKEN_AUDIENCE,
    key: str = PRIVATE_PEM,
    algorithm: str = main.AUTH_TOKEN_ALGORITHM,
) -> str:
    now = int(time.time())
    claims = {
        "sub": username,
        "role": role,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": expires_at if expires_at is not None else now + 3600,
    }
    return jwt.encode(claims, key, algorithm=algorithm)


def install_public_key(monkeypatch, directory: Path) -> None:
    key_path = directory / "jwt-public.pem"
    key_path.write_text(PUBLIC_PEM, encoding="utf-8")
    monkeypatch.setenv(main.AUTH_PUBLIC_KEY_PATH_ENV, str(key_path))
    main.token_verification_key.cache_clear()
