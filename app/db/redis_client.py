import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=2.0,
    socket_connect_timeout=2.0,
)