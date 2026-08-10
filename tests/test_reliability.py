import pytest
from unittest.mock import patch
from redis.exceptions import RedisError
import httpx


def test_request_id_generated_when_missing(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_existing_request_id_preserved(api_client):
    custom_id = "my-custom-trace-id-123"
    response = api_client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["x-request-id"] == custom_id


def test_request_id_returned_in_response(api_client):
    response = api_client.get("/health")
    assert response.headers.get("x-request-id") is not None


def test_health_liveness_succeeds(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_succeeds_when_dependencies_available(api_client):
    response = api_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["dependencies"]["database"] == "ok"
    assert body["dependencies"]["redis"] == "ok"


def test_readiness_fails_when_redis_unavailable(api_client):
    from app.db.redis_client import redis_client
    with patch.object(redis_client, "ping", side_effect=RedisError("connection refused")):
        response = api_client.get("/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert body["dependencies"]["redis"] == "unreachable"


def test_error_response_contains_request_id(api_client):
    response = api_client.get("/api/v1/auth/me")  # no auth -> 401
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "request_id" in body["error"]
    assert body["error"]["request_id"] is not None


def test_rate_limiter_fails_open_when_redis_down(api_client):
    from app.core import rate_limiter
    with patch.object(
        rate_limiter.redis_client, "zremrangebyscore",
        side_effect=RedisError("connection refused"),
    ):
        # Should NOT raise or return 500 — must fail open and let the
        # request continue normally.
        rate_limiter.check_rate_limit(user_id=999002, plan="free", request_id="test-id")
        # If we reach this line without an exception, fail-open worked.
        assert True


def test_downstream_timeout_handled_correctly(api_client, auth_token):
    from app.services import external_client

    async def mock_timeout(*args, **kwargs):
        raise httpx.TimeoutException("simulated timeout")

    with patch("httpx.AsyncClient.get", side_effect=mock_timeout):
        response = api_client.get(
            "/gateway/external-check?delay=8",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 504
        body = response.json()
        assert body["success"] is False
        assert "request_id" in body["error"]