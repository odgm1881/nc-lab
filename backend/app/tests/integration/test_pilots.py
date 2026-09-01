def _card(auth_client, name: str, vendor_code: str) -> dict:
    response = auth_client.post(
        "/api/cards",
        json={"name": name, "vendor_code": vendor_code, "category_code": "6201"},
    )
    assert response.status_code == 201
    return response.json()


def test_managed_pilot_lifecycle_freezes_sample_and_exports_report(auth_client) -> None:
    first = _card(auth_client, "Куртка", "J-1")
    second = _card(auth_client, "Брюки", "T-1")

    created = auth_client.post(
        "/api/pilots",
        json={
            "name": "Пилот августа",
            "description": "Проверка первой выборки",
            "sample_target": 2,
            "planned_start_date": "2026-08-24",
            "planned_end_date": "2026-08-31",
            "responsible": "Анна Иванова",
            "participants": ["Анна Иванова", "Пётр Петров", "Анна Иванова"],
            "baseline_time_per_card_minutes": 90,
            "baseline_first_pass_rate": 40,
            "baseline_return_rate": 30,
            "baseline_labor_minutes_per_card": 60,
            "operator_hourly_cost": 1200,
        },
    )
    assert created.status_code == 201
    pilot = created.json()
    assert pilot["status"] == "preparation"
    assert pilot["participants"] == ["Анна Иванова", "Пётр Петров"]
    assert pilot["cards_count"] == 0
    assert pilot["baseline_time_per_card_minutes"] == 90
    assert pilot["effect"]["measured_indicators"] == 0

    added = auth_client.post(
        f"/api/pilots/{pilot['id']}/cards",
        json={"card_ids": [first["id"], second["id"], first["id"]]},
    )
    assert added.status_code == 200
    assert added.json()["cards_count"] == 2
    assert added.json()["metrics"]["pilot_sample_reached"] is True
    assert added.json()["effect"]["baseline_cost_per_card"] == 1200

    started = auth_client.post(f"/api/pilots/{pilot['id']}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "running"
    assert started.json()["started_at"] is not None

    frozen = auth_client.delete(f"/api/pilots/{pilot['id']}/cards/{first['id']}")
    assert frozen.status_code == 409
    assert "зафиксирован" in frozen.json()["error"]["message"]

    completed = auth_client.post(f"/api/pilots/{pilot['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None

    report = auth_client.get(f"/api/pilots/{pilot['id']}/report.csv")
    assert report.status_code == 200
    assert "Пилот августа" in report.content.decode("utf-8-sig")
    assert "J-1" in report.content.decode("utf-8-sig")
    assert "effect_metric" in report.content.decode("utf-8-sig")


def test_pilot_baseline_validation_and_update(auth_client) -> None:
    invalid = auth_client.post(
        "/api/pilots",
        json={"name": "Пилот", "baseline_first_pass_rate": 101},
    )
    assert invalid.status_code == 422

    pilot = auth_client.post("/api/pilots", json={"name": "Пилот"}).json()
    updated = auth_client.patch(
        f"/api/pilots/{pilot['id']}",
        json={"baseline_cost_per_card": 350.5, "operator_hourly_cost": 900},
    )
    assert updated.status_code == 200
    assert updated.json()["baseline_cost_per_card"] == 350.5
    assert updated.json()["effect"]["baseline_cost_per_card"] == 350.5


def test_pilot_requires_cards_to_start_and_is_tenant_isolated(auth_client, client) -> None:
    pilot = auth_client.post("/api/pilots", json={"name": "Пустой пилот"}).json()
    empty_start = auth_client.post(f"/api/pilots/{pilot['id']}/start")
    assert empty_start.status_code == 400

    client.post(
        "/api/auth/register",
        json={
            "email": "other@test.ru",
            "password": "password",
            "full_name": "Другой",
            "client_name": "Другой клиент",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "other@test.ru", "password": "password"},
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    assert client.get(f"/api/pilots/{pilot['id']}").status_code == 404
    assert client.get("/api/pilots").json()["total"] == 0


def test_pilot_rejects_invalid_period(auth_client) -> None:
    response = auth_client.post(
        "/api/pilots",
        json={
            "name": "Неверный период",
            "planned_start_date": "2026-09-10",
            "planned_end_date": "2026-09-01",
        },
    )
    assert response.status_code == 422
