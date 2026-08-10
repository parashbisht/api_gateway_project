from fastapi import APIRouter, Response, status
from sqlalchemy import text
from app.db.session import SessionLocal
from app.db.redis_client import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness_check():
    """
    Liveness only: is the FastAPI process itself running?
    No DB or Redis calls — must stay fast and dependency-free.
    """
    return {"status": "alive"}


@router.get("/ready")
def readiness_check(response: Response):
    """
    Readiness: are required dependencies (Postgres, Redis) reachable?
    """
    db_status = "ok"
    redis_status = "ok"

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "unreachable"

    try:
        redis_client.ping()
    except Exception:
        redis_status = "unreachable"

    is_ready = db_status == "ok" and redis_status == "ok"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
        },
    }