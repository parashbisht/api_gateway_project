def test_create_api_key(api_client, auth_token):
    response = api_client.post(
        "/api/v1/api-keys",
        json={"name": "test key"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["raw_key"].startswith("sk_live_")


def test_list_api_keys_excludes_raw_key(api_client, auth_token):
    api_client.post(
        "/api/v1/api-keys",
        json={"name": "test key"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    response = api_client.get(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    for key in response.json():
        assert "raw_key" not in key  # security check


def test_disable_api_key(api_client, auth_token):
    create_response = api_client.post(
        "/api/v1/api-keys",
        json={"name": "to disable"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    key_id = create_response.json()["id"]

    disable_response = api_client.patch(
        f"/api/v1/api-keys/{key_id}/disable",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["active"] is False


def test_create_api_key_requires_auth(api_client):
    response = api_client.post("/api/v1/api-keys", json={"name": "no auth"})
    assert response.status_code == 401