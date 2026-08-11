"""
Integration tests against a REAL Redis instance (not mocked) — verifies
actual key creation, timestamp storage, expiration, and cleanup behavior.
Requires Redis to be running (already true for local dev / Docker Compose).
"""
from app.db.redis_client import redis_client


def test_redis_key_created_with_correct_format(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    api_client.get("/gateway/ping", headers=headers)

    keys = redis_client.keys("ratelimit:user:free:*")
    assert len(keys) >= 1


def test_redis_sorted_set_stores_timestamps(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    api_client.get("/gateway/ping", headers=headers)

    keys = redis_client.keys("ratelimit:user:free:*")
    assert len(keys) >= 1
    entries = redis_client.zrange(keys[0], 0, -1, withscores=True)
    assert len(entries) >= 1
    for member, score in entries:
        assert score > 0  # a real Unix timestamp


def test_redis_key_has_ttl_set(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    api_client.get("/gateway/ping", headers=headers)

    keys = redis_client.keys("ratelimit:user:free:*")
    ttl = redis_client.ttl(keys[0])
    assert ttl > 0  # key will expire, not live forever


def test_old_timestamps_removed_from_window(api_client):
    import uuid
    from app.db.redis_client import redis_client

    email = f"ttl_{uuid.uuid4().hex[:8]}@example.com"
    api_client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    login = api_client.post("/api/v1/auth/login", data={"username": email, "password": "testpass123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = api_client.get("/gateway/ping", headers=headers)
    # Extract the exact user id from the response body to build the exact key
    user_id = response.json()["user_id"]
    key = f"ratelimit:user:free:{user_id}"

    redis_client.zadd(key, {"fake-old-entry": 1})
    count_before = redis_client.zcard(key)
    assert count_before >= 2

    api_client.get("/gateway/ping", headers=headers)

    remaining_members = redis_client.zrange(key, 0, -1)
    assert "fake-old-entry" not in remaining_members