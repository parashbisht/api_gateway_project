from app.core import rate_limiter
from fastapi import HTTPException
import pytest


def test_rate_limiter_allows_requests_under_limit(monkeypatch):
    from app.core import plans
    monkeypatch.setitem(
        plans.PLAN_DETAILS,
        "test_plan",
        {"requests_per_hour": 3, "display_name": "Test", "can_access_premium_analytics": False},
    )

    test_user_id = 999001  # unlikely to collide with real user IDs
    key = f"ratelimit:user:test_plan:{test_user_id}"
    rate_limiter.redis_client.delete(key)  # clean slate, using the CURRENT key format

    # First 3 requests should succeed (limit is 3)
    for _ in range(3):
        rate_limiter.check_rate_limit(user_id=test_user_id, plan="test_plan")

    # 4th request should raise 429
    with pytest.raises(HTTPException) as exc_info:
        rate_limiter.check_rate_limit(user_id=test_user_id, plan="test_plan")
    assert exc_info.value.status_code == 429

    rate_limiter.redis_client.delete(key)  # cleanup with the correct key too