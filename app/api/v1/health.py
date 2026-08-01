from fastapi import APIRouter
from sqlalchemy import text
from app.db.session import SessionLocal
from app.db.redis_client import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
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

    overall = "healthy" if db_status == "ok" and redis_status == "ok" else "unhealthy"

    return {
        "status": overall,
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
        },
    }