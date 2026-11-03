import time

import jwt

from app.config import JWT_ALGORITHM

TEST_USER = "student"
TEST_ROLE = "STUDENT"
TEST_JWT_SECRET = "test-only-ai-labs-signing-key-not-for-production"
TEST_JWT_ISSUER = "ai-labs-tests"
TEST_JWT_AUDIENCE = "ai-labs-api-tests"
TOKEN_LIFETIME_SECONDS = 3600


def make_token(
    username: str = TEST_USER,
    role: str = TEST_ROLE,
    *,
    issuer: str = TEST_JWT_ISSUER,
    audience: str = TEST_JWT_AUDIENCE,
    expires_at: int | None = None,
    signing_key: str = TEST_JWT_SECRET,
    omit_claims: tuple[str, ...] = (),
) -> str:
    claims = {
        "sub": username,
        "role": role,
        "exp": expires_at if expires_at is not None else int(time.time()) + TOKEN_LIFETIME_SECONDS,
        "iss": issuer,
        "aud": audience,
    }
    for claim in omit_claims:
        claims.pop(claim, None)
    return jwt.encode(claims, signing_key, algorithm=JWT_ALGORITHM)


def auth_headers(username: str = TEST_USER, role: str = TEST_ROLE) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(username, role)}"}
