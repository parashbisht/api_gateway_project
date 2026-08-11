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