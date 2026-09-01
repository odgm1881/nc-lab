from sqlalchemy import select

from app.database import SessionLocal
from app.modules.auth.models import ROLE_OPERATOR, User


def _promote_current_user() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@test.ru"))
        assert user is not None
        user.role = ROLE_OPERATOR
        db.commit()


def test_ruleset_approval_applies_by_category_and_keeps_history(auth_client) -> None:
    forbidden = auth_client.post(
        "/api/validation/rulesets",
        json={
            "version": "2.1.0",
            "title": "Правила для одежды",
            "category_codes": ["6201"],
            "source_reference": "Методические рекомендации НК от 20.08.2026",
            "change_summary": "Уточнены проверки одежды.",
            "effective_from": "2026-01-01",
        },
    )
    assert forbidden.status_code == 403

    _promote_current_user()
    created = auth_client.post(
        "/api/validation/rulesets",
        json={
            "version": "2.1.0",
            "title": "Правила для одежды",
            "category_codes": ["6201", "6201"],
            "source_reference": "Методические рекомендации НК от 20.08.2026",
            "change_summary": "Уточнены проверки одежды.",
            "effective_from": "2026-01-01",
        },
    )
    assert created.status_code == 201
    ruleset = created.json()
    assert ruleset["status"] == "draft"
    assert ruleset["category_codes"] == ["6201"]
    assert ruleset["rule_names"]

    approved = auth_client.post(
        f"/api/validation/rulesets/{ruleset['id']}/approve",
        json={"expert_name": "Эксперт НК"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_by_name"] == "Эксперт НК"

    clothing = auth_client.post(
        "/api/cards",
        json={"name": "Куртка", "vendor_code": "J-1", "category_code": "6201"},
    ).json()
    validated = auth_client.post(f"/api/cards/{clothing['id']}/validate")
    assert validated.status_code == 200
    assert validated.json()["card"]["ruleset_version"] == "2.1.0"
    assert validated.json()["result"]["ruleset_version"] == "2.1.0"

    other = auth_client.post(
        "/api/cards",
        json={"name": "Прочее", "vendor_code": "O-1", "category_code": "9999"},
    ).json()
    other_validated = auth_client.post(f"/api/cards/{other['id']}/validate")
    assert other_validated.json()["card"]["ruleset_version"] == "1.0.0"

    history = auth_client.get(f"/api/validation/rulesets/{ruleset['id']}/history")
    assert history.status_code == 200
    assert {event["action"] for event in history.json()} == {
        "validation_ruleset.created",
        "validation_ruleset.approved",
    }

    retired = auth_client.post(f"/api/validation/rulesets/{ruleset['id']}/retire")
    assert retired.status_code == 200
    check = auth_client.post(
        "/api/validation/check",
        json={"category_code": "6201"},
    )
    assert check.json()["ruleset_version"] == "1.0.0"


def test_ruleset_rejects_duplicate_version_and_invalid_period(auth_client) -> None:
    _promote_current_user()
    payload = {
        "version": "3.0.0",
        "title": "Новая версия",
        "source_reference": "Регламент НК",
        "effective_from": "2026-09-10",
        "effective_to": "2026-09-01",
    }
    assert auth_client.post("/api/validation/rulesets", json=payload).status_code == 422
    payload.pop("effective_to")
    assert auth_client.post("/api/validation/rulesets", json=payload).status_code == 201
    assert auth_client.post("/api/validation/rulesets", json=payload).status_code == 409


def test_approved_ruleset_executes_its_stored_rule_snapshot(auth_client) -> None:
    _promote_current_user()
    rule_names = [
        "rule_category_known",
        "rule_required_attributes",
        "rule_gtin_format",
        "rule_gtin_unique_per_card",
        "rule_rd_present_and_structured",
    ]
    created = auth_client.post(
        "/api/validation/rulesets",
        json={
            "version": "4.0.0",
            "title": "Профиль без проверки смешанных вариаций",
            "category_codes": ["6109"],
            "rule_names": rule_names,
            "source_reference": "Тестовый утверждённый профиль",
            "effective_from": "2026-01-01",
        },
    )
    assert created.status_code == 201, created.text
    ruleset = created.json()
    assert ruleset["rule_names"] == rule_names
    assert auth_client.post(
        f"/api/validation/rulesets/{ruleset['id']}/approve",
        json={},
    ).status_code == 200

    response = auth_client.post(
        "/api/validation/check",
        json={
            "category_code": "6109",
            "gtin": "4600000000015",
            "attributes": {
                "item_type": "футболка",
                "composition": "хлопок",
                "size": "M",
                "color": "чёрный, белый",
                "gender": "мужской",
                "age_group": "взрослая",
            },
            "rd_data": {
                "type": "declaration",
                "number": "Д-1",
                "date": "2026-01-01",
                "valid_until": "2029-01-01",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["ruleset_version"] == "4.0.0"
    assert response.json()["is_valid"] is True
    assert "VARIATION_MIXED" not in {
        issue["code"] for issue in response.json()["issues"]
    }


def test_ruleset_cannot_disable_blocking_category_rule(auth_client) -> None:
    _promote_current_user()
    response = auth_client.post(
        "/api/validation/rulesets",
        json={
            "version": "5.0.0",
            "title": "Небезопасный профиль",
            "rule_names": ["rule_gtin_format"],
            "source_reference": "Тестовый профиль",
            "effective_from": "2026-01-01",
        },
    )
    assert response.status_code == 400
    assert "обязательные правила" in response.json()["error"]["message"]
