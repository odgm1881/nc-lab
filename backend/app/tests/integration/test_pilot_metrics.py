from sqlalchemy import select

from app.database import SessionLocal
from app.modules.auth.models import ROLE_OPERATOR, User
from app.tests.integration.test_cards_flow import VALID_CARD


def _make_current_user_operator() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@test.ru"))
        assert user is not None
        user.role = ROLE_OPERATOR
        db.commit()


def test_pilot_metrics_cover_import_readiness_and_operator_work(auth_client) -> None:
    content = (
        "Наименование;Артикул;Категория;GTIN;Вид изделия;Цвет;Размер;Пол;Состав;"
        "Возрастная группа;Тип РД;Номер РД;Дата РД;Срок действия\n"
        "Джемпер;P-1;6110;4600000000015;джемпер;серый;M;женский;шерсть 80%;"
        "взрослая;certificate;C-1;2026-01-15;2028-01-15\n"
    ).encode()
    committed = auth_client.post(
        "/api/import/commit",
        files={"file": ("pilot.csv", content, "text/csv")},
        data={"create_cards": "true"},
    )
    assert committed.status_code == 201, committed.text
    job_id = committed.json()["job_id"]
    card_id = auth_client.get(f"/api/import/jobs/{job_id}/rows").json()[0]["card_id"]
    assert auth_client.post(f"/api/cards/{card_id}/ready").status_code == 200

    task = auth_client.post(
        "/api/operator/tasks",
        json={
            "card_id": card_id,
            "title": "Проверить карточку",
            "escalation_reason": "Спорное значение состава",
            "priority": 3,
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]
    _make_current_user_operator()
    assert auth_client.patch(
        f"/api/operator/tasks/{task_id}", json={"status": "in_progress"}
    ).status_code == 200
    resolved = auth_client.patch(
        f"/api/operator/tasks/{task_id}",
        json={"status": "resolved", "resolution": "Состав подтверждён клиентом"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["started_at"]
    assert resolved.json()["resolved_at"]

    response = auth_client.get("/api/pilot/metrics")
    assert response.status_code == 200, response.text
    metrics = response.json()
    assert metrics["cards_total"] == 1
    assert metrics["cards_ready"] == 1
    assert metrics["import_success_rate"] == 100.0
    assert metrics["first_pass_validation_rate"] == 100.0
    assert metrics["operator_resolution_rate"] == 100.0
    assert metrics["median_time_to_ready_minutes"] is not None
    assert metrics["pilot_sample_reached"] is False

    csv_response = auth_client.get("/api/pilot/metrics.csv")
    assert csv_response.status_code == 200
    assert "first_pass_validation_rate" in csv_response.content.decode("utf-8-sig")


def test_operator_resolution_is_required(auth_client) -> None:
    card_id = auth_client.post("/api/cards", json=VALID_CARD).json()["id"]
    task_id = auth_client.post(
        "/api/operator/tasks", json={"card_id": card_id, "title": "Проверить"}
    ).json()["id"]
    _make_current_user_operator()

    response = auth_client.patch(
        f"/api/operator/tasks/{task_id}", json={"status": "resolved"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TASK_RESOLUTION_REQUIRED"
