import base64
import time

TEST_USER = "student"
TEST_ROLE = "STUDENT"
LEGACY_TEST_SECRET = "WORKSHOP_SECRET_2026"
TOKEN_LIFETIME_SECONDS = 3600


def make_token(username: str = TEST_USER, role: str = TEST_ROLE) -> str:
    expires_at = int(time.time()) + TOKEN_LIFETIME_SECONDS
    raw = f"{username}|{role}|{expires_at}|{LEGACY_TEST_SECRET}"
    return base64.b64encode(raw.encode()).decode()


def auth_headers(username: str = TEST_USER, role: str = TEST_ROLE) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(username, role)}"}
