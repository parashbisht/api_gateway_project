import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def api_client():
    return client


@pytest.fixture
def registered_user(api_client):
    """
    Creates a fresh user with a unique email for each test that needs one,
    avoiding 'already registered' collisions between test runs.
    """
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpass123"

    api_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    return {"email": email, "password": password}


@pytest.fixture
def auth_token(api_client, registered_user):
    """Returns a valid JWT for a freshly registered user."""
    response = api_client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    return response.json()["access_token"]

@pytest.fixture(autouse=True)
def clear_login_rate_limit():
    from app.db.redis_client import redis_client
    redis_client.delete("login_attempts:testclient")
    yield