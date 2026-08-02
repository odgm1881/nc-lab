"""Регрессия pilot-ready функций: аудит, импорт, массовые операции и изоляция."""

from fastapi.testclient import TestClient

from app.modules.catalog import service as catalog_service
from app.tests.integration.test_cards_flow import VALID_CARD


def test_validation_versions_card_fields_and_history(auth_client: TestClient) -> None:
    payload = {
        **VALID_CARD,
        "packaging": {"type": "короб", "units_per_package": 10},
        "data_source": "onec",
        "service_comment": "Проверить состав",
    }
    created = auth_client.post("/api/cards", json=payload)
    assert created.status_code == 201, created.text
    card_id = created.json()["id"]

    validated = auth_client.post(f"/api/cards/{card_id}/validate")
    assert validated.status_code == 200, validated.text
    body = validated.json()
    assert body["result"]["ruleset_version"] == "1.0.0"
    assert body["result"]["reference_data_version"] == "2026.08"
    assert body["card"]["packaging"]["units_per_package"] == 10
    assert body["card"]["data_source"] == "onec"
    assert body["card"]["ruleset_version"] == "1.0.0"

    cleared = auth_client.patch(
        f"/api/cards/{card_id}", json={"gtin": None, "service_comment": None}
    )
    assert cleared.status_code == 200
    assert cleared.json()["gtin"] is None
    assert cleared.json()["service_comment"] is None
    assert cleared.json()["ruleset_version"] is None

    history = auth_client.get(f"/api/cards/{card_id}/history")
    assert history.status_code == 200
    actions = {event["action"] for event in history.json()}
    assert {"card.created", "card.validated", "card.updated"} <= actions
    assert all(event["correlation_id"] for event in history.json())


def test_mapping_profile_row_protocol_and_error_report(auth_client: TestClient) -> None:
    profile = auth_client.post(
        "/api/import/mapping-profiles",
        json={
            "name": "Пилот 1С",
            "source": "csv",
            "mapping": {"Товар пилота": "name", "Внутренний код": "vendor_code"},
        },
    )
    assert profile.status_code == 201, profile.text
    profile_id = profile.json()["id"]
    content = "Товар пилота;Внутренний код\nФутболка;A-1\n;\n".encode()

    preview = auth_client.post(
        "/api/import/preview",
        files={"file": ("pilot.csv", content, "text/csv")},
        data={"profile_id": profile_id},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["rows"][0]["name"] == "Футболка"

    committed = auth_client.post(
        "/api/import/commit",
        files={"file": ("pilot.csv", content, "text/csv")},
        data={"profile_id": profile_id, "create_cards": "true"},
    )
    assert committed.status_code == 201, committed.text
    result = committed.json()
    assert result["cards_created"] == 1
    assert result["rows_error"] == 1  # карточка создана, но не проходит доменные правила

    rows = auth_client.get(f"/api/import/jobs/{result['job_id']}/rows")
    assert rows.status_code == 200
    assert rows.json()[0]["status"] == "imported_with_errors"
    assert rows.json()[0]["errors"]

    history = auth_client.get(f"/api/cards/{rows.json()[0]['card_id']}/history")
    assert history.status_code == 200
    assert history.json()[0]["action"] == "card.created"
    assert history.json()[0]["details"]["origin"] == "import"

    report = auth_client.get(f"/api/import/jobs/{result['job_id']}/error-report")
    assert report.status_code == 200
    assert "GTIN_MISSING" in report.content.decode("utf-8-sig")


def test_bulk_update_and_export_are_scoped_and_csv_safe(auth_client: TestClient) -> None:
    first = auth_client.post(
        "/api/cards", json={**VALID_CARD, "name": "=WEBSERVICE(\"bad\")"}
    ).json()
    second = auth_client.post(
        "/api/cards", json={**VALID_CARD, "gtin": None, "vendor_code": "JMP-2"}
    ).json()

    updated = auth_client.patch(
        "/api/cards/bulk",
        json={
            "ids": [first["id"], second["id"]],
            "data_source": "excel",
            "service_comment": "Пакетная правка",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["updated"] == 2
    assert auth_client.get(f"/api/cards/{second['id']}").json()["data_source"] == "excel"

    exported = auth_client.post("/api/cards/export", json={"ids": [first["id"]]})
    assert exported.status_code == 200
    text = exported.content.decode("utf-8-sig")
    assert "'=WEBSERVICE" in text
    assert "JMP-2" not in text

    filtered = auth_client.post("/api/cards/export", json={"name": second["name"]})
    assert filtered.status_code == 200
    filtered_text = filtered.content.decode("utf-8-sig")
    assert "JMP-2" in filtered_text
    assert "'=WEBSERVICE" not in filtered_text


def test_export_does_not_silently_truncate(auth_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        catalog_service.repo,
        "list_cards",
        lambda *args, **kwargs: ([], 5001),
    )

    response = auth_client.post("/api/cards/export", json={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EXPORT_LIMIT_EXCEEDED"


def test_same_organization_name_does_not_join_existing_tenant(client: TestClient) -> None:
    def register(email: str) -> tuple[str, str]:
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "password",
                "full_name": email,
                "client_name": "Одинаковое ООО",
            },
        )
        token = client.post(
            "/api/auth/login", json={"email": email, "password": "password"}
        ).json()["access_token"]
        return response.json()["client_id"], token

    client_a, token_a = register("first@example.ru")
    client_b, token_b = register("second@example.ru")
    assert client_a != client_b
    client.post(
        "/api/cards",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Секретная карточка", "vendor_code": "PRIVATE"},
    )
    listed = client.get(
        "/api/cards", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert listed.json()["total"] == 0
