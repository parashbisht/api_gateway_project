import time
import uuid
from fastapi import HTTPException, status

from app.db.redis_client import redis_client

PLAN_LIMITS = {
    "free": {"requests": 100, "window_seconds": 3600},
    "premium": {"requests": 5000, "window_seconds": 3600},
    "enterprise": None,  
}

def check_rate_limit(user_id: int, plan: str) -> None:
    """
    Raises HTTP 429 if the user has exceeded their plan's rate limit.
    Uses a sliding window implemented with a Redis sorted set.
    """
    limit_config = PLAN_LIMITS.get(plan)

    if limit_config is None:
        return  

    max_requests = limit_config["requests"]
    window_seconds = limit_config["window_seconds"]

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