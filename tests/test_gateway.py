def test_gateway_ping_with_valid_token(api_client, auth_token):
    response = api_client.get(
        "/gateway/ping",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert "user_id" in response.json()


def test_gateway_ping_with_no_auth(api_client):
    response = api_client.get("/gateway/ping")
    assert response.status_code == 401


def test_create_and_list_products(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    create_response = api_client.post(
        "/gateway/products",
        json={"name": "Test Product", "price": 9.99},
        headers=headers,
    )
    assert create_response.status_code == 201

    list_response = api_client.get("/gateway/products", headers=headers)
    assert list_response.status_code == 200
    assert any(p["name"] == "Test Product" for p in list_response.json())


def test_health_check_returns_healthy(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"