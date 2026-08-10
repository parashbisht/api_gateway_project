import time
import uuid
from fastapi import HTTPException, status

from app.db.redis_client import redis_client
from app.core.plans import PLAN_DETAILS
from app.core.config import settings


def check_rate_limit(user_id: int, plan: str) -> None:
    plan_info = PLAN_DETAILS.get(plan)

    if plan_info is None or plan_info["requests_per_hour"] is None:
        return  # unknown plan or unlimited (enterprise)

    max_requests = plan_info["requests_per_hour"]
    window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS

    key = f"rate_limit:{user_id}"
    now = time.time()
    window_start = now - window_seconds

    redis_client.zremrangebyscore(key, 0, window_start)
    current_count = redis_client.zcard(key)

    if current_count >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {max_requests} requests per "
                   f"{window_seconds} seconds for '{plan}' plan.",
        )

    member = f"{now}-{uuid.uuid4()}"
    redis_client.zadd(key, {member: now})
    redis_client.expire(key, window_seconds)

    
def check_login_rate_limit(ip_address: str) -> None:
    key = f"login_attempts:{ip_address}"
    max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
    window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS

    now = time.time()
    window_start = now - window_seconds

    redis_client.zremrangebyscore(key, 0, window_start)
    current_count = redis_client.zcard(key)

    if current_count >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

    member = f"{now}-{uuid.uuid4()}"
    redis_client.zadd(key, {member: now})
    redis_client.expire(key, window_seconds)