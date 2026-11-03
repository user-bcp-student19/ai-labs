import logging

import jwt
from fastapi import HTTPException
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ValidationError

from app.config import AuthSettings, JWT_ALGORITHM

FORBIDDEN_DETAIL = "Forbidden"
FORBIDDEN_STATUS_CODE = 403
UNAUTHORIZED_DETAIL = "Invalid or expired token"
UNAUTHORIZED_STATUS_CODE = 401
BEARER_CHALLENGE = "Bearer"
LOGGER = logging.getLogger(__name__)


class Identity(BaseModel):
    username: str
    role: str


def decode_access_token(token: str, settings: AuthSettings) -> Identity:
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["exp", "iss", "aud", "sub", "role"]},
    )
    try:
        return Identity(username=claims["sub"], role=claims["role"])
    except (KeyError, ValidationError) as error:
        raise InvalidTokenError("Invalid identity claims") from error


def authenticate_bearer(authorization: str, settings: AuthSettings) -> Identity:
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != BEARER_CHALLENGE.lower() or not separator or not token:
        raise _unauthorized()

    try:
        return decode_access_token(token, settings)
    except InvalidTokenError as error:
        LOGGER.warning("Token validation failed: %s", error)
        raise _unauthorized() from error


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=UNAUTHORIZED_STATUS_CODE,
        detail=UNAUTHORIZED_DETAIL,
        headers={"WWW-Authenticate": BEARER_CHALLENGE},
    )


def resolve_owner(identity: dict[str, str], requested_owner: str | None) -> str:
    username = identity["username"]
    if not requested_owner or requested_owner == username:
        return username
    raise HTTPException(status_code=FORBIDDEN_STATUS_CODE, detail=FORBIDDEN_DETAIL)
