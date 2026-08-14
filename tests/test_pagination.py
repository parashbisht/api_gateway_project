def test_products_pagination_respects_limit(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    for i in range(5):
        api_client.post("/gateway/products", json={"name": f"PagTest{i}", "price": 1.0}, headers=headers)

    response = api_client.get("/gateway/products?limit=2&offset=0", headers=headers)
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total"] >= 5


def test_products_pagination_rejects_invalid_limit(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = api_client.get("/gateway/products?limit=9999", headers=headers)
    assert response.status_code == 422


def test_products_sort_by_whitelisted_field(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = api_client.get("/gateway/products?sort_by=price", headers=headers)
    assert response.status_code == 200


def test_products_sort_by_invalid_field_rejected(api_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = api_client.get("/gateway/products?sort_by=malicious_column", headers=headers)
    assert response.status_code == 422