import time
from fastapi import Request
from app.db.session import SessionLocal
from app.models.request_log import RequestLog
from app.models.api_key import APIKey
from app.core.security import decode_access_token, verify_api_key


def _identify_user_from_jwt(auth_header: str | None, db) -> int | None:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.replace("Bearer ", "")
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    return int(user_id) if user_id else None


def _identify_user_from_api_key(x_api_key: str | None, db) -> int | None:
    if not x_api_key:
        return None
    prefix = x_api_key[:14]
    candidates = db.query(APIKey).filter(
        APIKey.prefix == prefix,
        APIKey.active == True,
    ).all()
    for key_row in candidates:
        if verify_api_key(x_api_key, key_row.hashed_key):
            return key_row.user_id
    return None


async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000

    db = SessionLocal()
    try:
        # Best-effort identification: try JWT first, then API key.
        # Never raises — logging must not block or break the request either way.
        user_id = _identify_user_from_jwt(request.headers.get("Authorization"), db)
        if user_id is None:
            user_id = _identify_user_from_api_key(request.headers.get("X-API-Key"), db)

        log_entry = RequestLog(
            user_id=user_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=request.client.host if request.client else "unknown",
            status_code=response.status_code,
            response_time_ms=round(duration_ms, 2),
        )
        db.add(log_entry)
        db.commit()
    finally:
        db.close()

    return response