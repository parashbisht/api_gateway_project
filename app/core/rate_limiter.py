import time
import uuid
from fastapi import HTTPException, status
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.db.redis_client import redis_client
from app.core.plans import PLAN_DETAILS
from app.core.config import settings
from app.core.logger import get_logger
from app.core.rate_limit_script import RATE_LIMIT_LUA

logger = get_logger("api_gateway.rate_limiter")

_rate_limit_script = redis_client.register_script(RATE_LIMIT_LUA)


class RateLimitResult:
    """Carries the outcome of a rate-limit check so callers (deps.py) can
    set response headers without re-querying Redis."""
    def __init__(self, allowed: bool, limit: int, remaining: int, reset_at: float, retry_after: int = 0):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after


def _run_atomic_check(key: str, window_seconds: int, max_requests: int) -> RateLimitResult:
    now = time.time()
    member = f"{now}-{uuid.uuid4()}"

    allowed, count, limit, ref_ts = _rate_limit_script(
        keys=[key],
        args=[now, window_seconds, max_requests, member],
    )

    allowed = bool(allowed)
    remaining = max(0, limit - count) if allowed else 0
    reset_at = ref_ts + window_seconds
    retry_after = max(0, int(reset_at - now)) if not allowed else 0

    return RateLimitResult(allowed, int(limit), int(remaining), reset_at, retry_after)


def check_rate_limit(user_id: int, plan: str, request_id: str | None = None) -> RateLimitResult | None:
    plan_info = PLAN_DETAILS.get(plan)

    if plan_info is None or plan_info["requests_per_hour"] is None:
        return None  # enterprise / unknown plan = unlimited, no headers to report

    max_requests = plan_info["requests_per_hour"]
    window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
    key = f"ratelimit:user:{plan}:{user_id}"

    try:
        result = _run_atomic_check(key, window_seconds, max_requests)
    except (RedisError, RedisTimeoutError) as e:
        logger.error(
            "Redis unavailable during rate limit check — failing open",
            extra={"request_id": request_id, "error": str(e), "user_id": user_id},
        )
        return None  # fail open — no headers, request proceeds

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {max_requests} requests per "
                   f"{window_seconds} seconds for '{plan}' plan.",
            headers={"Retry-After": str(result.retry_after)},
        )

    return result


def check_login_rate_limit(ip_address: str, request_id: str | None = None) -> None:
    max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
    window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    key = f"ratelimit:login:ip:{ip_address}"

    try:
        result = _run_atomic_check(key, window_seconds, max_attempts)
    except (RedisError, RedisTimeoutError) as e:
        logger.error(
            "Redis unavailable during login rate limit check — failing open",
            extra={"request_id": request_id, "error": str(e), "ip_address": ip_address},
        )
        return

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(result.retry_after)},
        )