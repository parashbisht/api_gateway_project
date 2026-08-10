import time
import uuid
from fastapi import HTTPException, status
from redis.exceptions import RedisError

from app.db.redis_client import redis_client
from app.core.plans import PLAN_DETAILS
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("api_gateway.rate_limiter")


def check_rate_limit(user_id: int, plan: str, request_id: str | None = None) -> None:
    plan_info = PLAN_DETAILS.get(plan)

    if plan_info is None or plan_info["requests_per_hour"] is None:
        return

    max_requests = plan_info["requests_per_hour"]
    window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS

    key = f"rate_limit:{user_id}"
    now = time.time()
    window_start = now - window_seconds

    try:
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

    except RedisError as e:
        logger.error(
            "Redis unavailable during rate limit check — failing open",
            extra={"request_id": request_id, "error": str(e), "user_id": user_id},
        )
        return


def check_login_rate_limit(ip_address: str, request_id: str | None = None) -> None:
    key = f"login_attempts:{ip_address}"
    max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
    window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS

    now = time.time()
    window_start = now - window_seconds

    try:
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

    except RedisError as e:
        logger.error(
            "Redis unavailable during login rate limit check — failing open",
            extra={"request_id": request_id, "error": str(e), "ip_address": ip_address},
        )
        return