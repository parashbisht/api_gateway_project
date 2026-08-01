def test_register_new_user(api_client):
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == email
    assert "hashed_password" not in body  # security check: never leak the hash


def test_register_duplicate_email_fails(api_client, registered_user):
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": registered_user["email"], "password": "anotherpass123"},
    )
    assert response.status_code == 400


def test_register_weak_password_rejected(api_client):
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "weakpass@example.com", "password": "123"},
    )
    assert response.status_code == 422


def test_login_success(api_client, registered_user):
    response = api_client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_fails(api_client, registered_user):
    response = api_client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_protected_route_with_valid_token(api_client, auth_token):
    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200


def test_protected_route_with_no_token(api_client):
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_protected_route_with_invalid_token(api_client):
    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage_token_here"},
    )
    assert response.status_code == 401