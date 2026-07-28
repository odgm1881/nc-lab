from fastapi.testclient import TestClient


def _register_and_token(client: TestClient, suffix: str) -> str:
    email = f"{suffix}@test.ru"
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "password",
            "full_name": suffix,
            "client_name": f"Клиент {suffix}",
        },
    )
    return client.post(
        "/api/auth/login", json={"email": email, "password": "password"}
    ).json()["access_token"]


def test_card_crud_and_operator_escalation_are_tenant_isolated(client: TestClient) -> None:
    token_a = _register_and_token(client, "tenant-a")
    token_b = _register_and_token(client, "tenant-b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    created = client.post(
        "/api/cards",
        headers=headers_a,
        json={"name": "Чужая карточка", "vendor_code": "PRIVATE-1"},
    )
    assert created.status_code == 201
    card_id = created.json()["id"]

    listed = client.get("/api/cards", headers=headers_b)
    assert listed.status_code == 200
    assert listed.json()["total"] == 0

    for method, path, payload in [
        ("get", f"/api/cards/{card_id}", None),
        ("patch", f"/api/cards/{card_id}", {"name": "Взлом"}),
        ("delete", f"/api/cards/{card_id}", None),
        ("post", f"/api/cards/{card_id}/validate", None),
        ("post", f"/api/cards/{card_id}/ready", None),
    ]:
        kwargs = {"headers": headers_b}
        if payload is not None:
            kwargs["json"] = payload
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 404

    escalation = client.post(
        "/api/operator/tasks",
        headers=headers_b,
        json={"card_id": card_id, "title": "Чужая задача", "priority": 1},
    )
    assert escalation.status_code == 404

    assert client.get(f"/api/cards/{card_id}", headers=headers_a).status_code == 200
