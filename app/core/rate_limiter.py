import time
import uuid
from fastapi import HTTPException, status

from app.db.redis_client import redis_client
from app.core.plans import PLAN_DETAILS


def check_rate_limit(user_id: int, plan: str) -> None:
    plan_info = PLAN_DETAILS.get(plan)

    if plan_info is None or plan_info["requests_per_hour"] is None:
        return  # unknown plan or unlimited (enterprise)

    max_requests = plan_info["requests_per_hour"]
    window_seconds = 3600

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
    """
    Separate, stricter limit for login attempts, keyed by IP instead of
    user_id — since we don't know who the user is until AFTER they
    successfully authenticate. Prevents brute-force password guessing.
    """
    key = f"login_attempts:{ip_address}"
    max_attempts = 10
    window_seconds = 300  # 5 minutes

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