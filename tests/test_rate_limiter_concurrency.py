import threading
from unittest.mock import patch


def test_concurrent_requests_do_not_exceed_limit(api_client, auth_token):
    """
    Fires many concurrent requests against a low, deterministic limit and
    verifies the atomic Lua script never allows more than the configured
    limit through, even under real thread-level concurrency.
    """
    from app.core import plans

    with patch.dict(
        plans.PLAN_DETAILS,
        {"free": {"requests_per_hour": 10, "display_name": "Free", "can_access_premium_analytics": False}},
    ):
        headers = {"Authorization": f"Bearer {auth_token}"}
        results = []
        lock = threading.Lock()

        def make_request():
            response = api_client.get("/gateway/ping", headers=headers)
            with lock:
                results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed_count = results.count(200)
        rejected_count = results.count(429)

        assert allowed_count <= 10, f"Expected at most 10 allowed, got {allowed_count}"
        assert allowed_count + rejected_count == 30


def test_concurrent_requests_at_exact_limit(api_client, auth_token):
    """Fires exactly the limit's worth of concurrent requests — all should succeed."""
    from app.core import plans

    with patch.dict(
        plans.PLAN_DETAILS,
        {"free": {"requests_per_hour": 5, "display_name": "Free", "can_access_premium_analytics": False}},
    ):
        headers = {"Authorization": f"Bearer {auth_token}"}
        results = []
        lock = threading.Lock()

        def make_request():
            response = api_client.get("/gateway/ping", headers=headers)
            with lock:
                results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(200) == 5


def test_concurrent_requests_from_different_users_dont_interfere(api_client):
    """Two different users hitting the limit concurrently should each get
    their own independent bucket, not share one."""
    import uuid
    from app.core import plans

    with patch.dict(
        plans.PLAN_DETAILS,
        {"free": {"requests_per_hour": 3, "display_name": "Free", "can_access_premium_analytics": False}},
    ):
        tokens = []
        for _ in range(2):
            email = f"concurrent_{uuid.uuid4().hex[:8]}@example.com"
            api_client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
            login = api_client.post(
                "/api/v1/auth/login", data={"username": email, "password": "testpass123"}
            )
            tokens.append(login.json()["access_token"])

        results = {0: [], 1: []}
        lock = threading.Lock()

        def make_request(user_index, token):
            headers = {"Authorization": f"Bearer {token}"}
            response = api_client.get("/gateway/ping", headers=headers)
            with lock:
                results[user_index].append(response.status_code)

        threads = []
        for user_index, token in enumerate(tokens):
            for _ in range(3):
                threads.append(threading.Thread(target=make_request, args=(user_index, token)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each user independently should have all 3 succeed — proving
        # separate Redis buckets per user, no cross-contamination.
        assert results[0].count(200) == 3
        assert results[1].count(200) == 3