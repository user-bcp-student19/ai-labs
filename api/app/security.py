from fastapi import HTTPException

FORBIDDEN_DETAIL = "Forbidden"
FORBIDDEN_STATUS_CODE = 403


def resolve_owner(identity: dict[str, str], requested_owner: str | None) -> str:
    username = identity["username"]
    if not requested_owner or requested_owner == username:
        return username
    raise HTTPException(status_code=FORBIDDEN_STATUS_CODE, detail=FORBIDDEN_DETAIL)
