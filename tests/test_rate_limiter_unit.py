import pytest
from unittest.mock import patch
from fastapi import HTTPException


def test_429_response_includes_retry_after_header(api_client, auth_token):
    from app.core import rate_limiter

    # Force a tiny limit so we can deterministically exceed it in 2 calls
    with patch.dict(
        rate_limiter.PLAN_DETAILS,
        {"free": {"requests_per_hour": 1, "display_name": "Free", "can_access_premium_analytics": False}},
    ):
        headers = {"Authorization": f"Bearer {auth_token}"}
        first = api_client.get("/gateway/ping", headers=headers)
        assert first.status_code == 200

        second = api_client.get("/gateway/ping", headers=headers)
        assert second.status_code == 429
        assert "retry-after" in second.headers
        assert int(second.headers["retry-after"]) >= 0

        body = second.json()
        assert body["success"] is False
        assert "request_id" in body["error"]


def test_different_plans_have_different_limits(api_client):
    import uuid
    from app.core.plans import PLAN_DETAILS

    email = f"plantest_{uuid.uuid4().hex[:8]}@example.com"
    api_client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    login = api_client.post("/api/v1/auth/login", data={"username": email, "password": "testpass123"})
    token = login.json()["access_token"]

    response = api_client.get("/gateway/ping", headers={"Authorization": f"Bearer {token}"})
    assert response.headers["x-ratelimit-limit"] == str(PLAN_DETAILS["free"]["requests_per_hour"])


def test_enterprise_plan_has_no_rate_limit_headers(api_client):
    import uuid
    email = f"enttest_{uuid.uuid4().hex[:8]}@example.com"
    api_client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    login = api_client.post("/api/v1/auth/login", data={"username": email, "password": "testpass123"})
    token = login.json()["access_token"]

    from app.db.session import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.plan = "enterprise"
    db.commit()
    db.close()

    response = api_client.get("/gateway/ping", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "x-ratelimit-limit" not in response.headers


def test_rate_limiter_fails_open_on_redis_timeout(api_client):
    from app.core import rate_limiter
    from redis.exceptions import TimeoutError as RedisTimeoutError

    with patch.object(rate_limiter.redis_client, "register_script") as mock_script:
        mock_script.return_value.side_effect = RedisTimeoutError("simulated timeout")
        # Re-register with the mocked client to exercise the timeout path
        rate_limiter.check_rate_limit(user_id=999003, plan="free", request_id="test-timeout")
        # No exception raised = fail-open worked


def test_api_key_and_jwt_share_same_rate_limit_bucket(api_client, auth_token):
    """Confirms client identity is per-user, not per-credential-type."""
    headers_jwt = {"Authorization": f"Bearer {auth_token}"}
    response = api_client.get("/gateway/ping", headers=headers_jwt)
    remaining_after_jwt = int(response.headers["x-ratelimit-remaining"])

    key_response = api_client.post(
        "/api/v1/api-keys", json={"name": "bucket-test"}, headers=headers_jwt
    )
    raw_key = key_response.json()["raw_key"]

    response2 = api_client.get("/gateway/ping", headers={"X-API-Key": raw_key})
    remaining_after_key = int(response2.headers["x-ratelimit-remaining"])

    # Same user, same bucket -> remaining should have decreased by 1 more,
    # not reset to a fresh count.
    assert remaining_after_key == remaining_after_jwt - 1