from app.core import rate_limiter
from fastapi import HTTPException
import pytest


def test_rate_limiter_allows_requests_under_limit(monkeypatch):
    monkeypatch.setitem(
        rate_limiter.PLAN_DETAILS if hasattr(rate_limiter, "PLAN_DETAILS") else {},
        "test_plan", {"requests_per_hour": 3}
    )
    # Directly patch PLAN_DETAILS imported into rate_limiter
    from app.core import plans
    monkeypatch.setitem(plans.PLAN_DETAILS, "test_plan", {"requests_per_hour": 3, "display_name": "Test", "can_access_premium_analytics": False})

    test_user_id = 999001  # unlikely to collide with real user IDs
    rate_limiter.redis_client.delete(f"rate_limit:{test_user_id}")  # clean slate

    # First 3 requests should succeed (limit is 3)
    for _ in range(3):
        rate_limiter.check_rate_limit(user_id=test_user_id, plan="test_plan")

    # 4th request should raise 429
    with pytest.raises(HTTPException) as exc_info:
        rate_limiter.check_rate_limit(user_id=test_user_id, plan="test_plan")

    assert exc_info.value.status_code == 429

    rate_limiter.redis_client.delete(f"rate_limit:{test_user_id}")  # cleanup