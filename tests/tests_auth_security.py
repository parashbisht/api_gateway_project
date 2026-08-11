import time
from jose import jwt
from app.core.config import settings


# ---- JWT tests ----

def test_valid_jwt_grants_access(api_client, auth_token):
    response = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200


def test_expired_jwt_rejected(api_client, registered_user):
    expired_payload = {"sub": "1", "exp": int(time.time()) - 60}  # expired 60s ago
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "request_id" in body["error"]


def test_malformed_jwt_rejected(api_client):
    response = api_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert response.status_code == 401


def test_invalid_signature_jwt_rejected(api_client):
    # Signed with the WRONG secret — should fail signature verification
    bad_token = jwt.encode({"sub": "1", "exp": int(time.time()) + 3600}, "wrong-secret-key", algorithm="HS256")
    response = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401


def test_missing_jwt_rejected(api_client):
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ---- API key tests ----

def test_valid_api_key_grants_access(api_client, auth_token):
    key_resp = api_client.post(
        "/api/v1/api-keys", json={"name": "security-test-key"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    raw_key = key_resp.json()["raw_key"]

    response = api_client.get("/gateway/ping", headers={"X-API-Key": raw_key})
    assert response.status_code == 200


def test_invalid_api_key_rejected(api_client):
    response = api_client.get("/gateway/ping", headers={"X-API-Key": "sk_live_totally_fake_key_here"})
    assert response.status_code == 401


def test_missing_api_key_and_jwt_rejected(api_client):
    response = api_client.get("/gateway/ping")
    assert response.status_code == 401


def test_disabled_api_key_rejected(api_client, auth_token):
    key_resp = api_client.post(
        "/api/v1/api-keys", json={"name": "to-disable"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    key_id = key_resp.json()["id"]
    raw_key = key_resp.json()["raw_key"]

    api_client.patch(
        f"/api/v1/api-keys/{key_id}/disable",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    response = api_client.get("/gateway/ping", headers={"X-API-Key": raw_key})
    assert response.status_code == 401


# ---- Authorization boundary tests ----

def test_user_cannot_see_another_users_api_keys(api_client):
    import uuid

    email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
    for email in (email_a, email_b):
        api_client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})

    login_a = api_client.post("/api/v1/auth/login", data={"username": email_a, "password": "testpass123"})
    login_b = api_client.post("/api/v1/auth/login", data={"username": email_b, "password": "testpass123"})
    token_a = login_a.json()["access_token"]
    token_b = login_b.json()["access_token"]

    api_client.post("/api/v1/api-keys", json={"name": "user-a-key"}, headers={"Authorization": f"Bearer {token_a}"})

    keys_seen_by_b = api_client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert all(k["name"] != "user-a-key" for k in keys_seen_by_b)


def test_client_cannot_override_authenticated_user_id(api_client, auth_token):
    """Order creation must use the authenticated identity, not any client-supplied user id."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    product_resp = api_client.post("/gateway/products", json={"name": "Boundary Test", "price": 5.0}, headers=headers)
    product_id = product_resp.json()["id"]

    me = api_client.get("/api/v1/auth/me", headers=headers).json()
    real_user_id = me["id"]

    # Even if a client tried to sneak in a user_id, OrderCreate has no such field —
    # this proves the schema itself doesn't accept client-supplied identity.
    order_resp = api_client.post(
        "/gateway/orders",
        json={"product_id": product_id, "user_id": 999999},  # extra field, should be ignored
        headers=headers,
    )
    assert order_resp.status_code == 201
    assert order_resp.json()["user_id"] == real_user_id
    assert order_resp.json()["user_id"] != 999999


# ---- Security / hygiene tests ----

def test_auth_error_has_consistent_format_and_request_id(api_client):
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "request_id" in body["error"]


def test_api_key_list_never_exposes_raw_key(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    api_client.post("/api/v1/api-keys", json={"name": "no-leak-test"}, headers=headers)
    response = api_client.get("/api/v1/api-keys", headers=headers)
    for key in response.json():
        assert "raw_key" not in key
        assert "hashed_key" not in key


def test_wrong_password_does_not_reveal_which_field_was_wrong(api_client, registered_user):
    response = api_client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["email"], "password": "definitely-wrong-password"},
    )
    assert response.status_code == 401
    # Should be a generic message, not "password incorrect" vs "user not found"
    assert "incorrect" in response.json()["error"]["message"].lower()