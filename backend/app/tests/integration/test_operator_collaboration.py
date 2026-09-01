from sqlalchemy import select

from app.database import SessionLocal
from app.modules.auth.models import ROLE_OPERATOR, User


def _promote_current_user() -> str:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@test.ru"))
        assert user is not None
        user.role = ROLE_OPERATOR
        db.commit()
        return user.id


def test_operator_comments_return_history_bulk_assignment_and_sorting(auth_client) -> None:
    card = auth_client.post(
        "/api/cards", json={"name": "Куртка", "vendor_code": "J-1"}
    ).json()
    first = auth_client.post(
        "/api/operator/tasks",
        json={
            "card_id": card["id"],
            "title": "Проверить РД",
            "category": "rd",
            "priority": 1,
        },
    )
    assert first.status_code == 201
    task_id = first.json()["id"]
    assert first.json()["category"] == "rd"

    second = auth_client.post(
        "/api/operator/tasks",
        json={"title": "Срочная проверка", "category": "other", "priority": 3},
    )
    assert second.status_code == 201

    my_tasks = auth_client.get("/api/operator/my-tasks", params={"card_id": card["id"]})
    assert my_tasks.status_code == 200
    assert [task["id"] for task in my_tasks.json()["items"]] == [task_id]

    client_comment = auth_client.post(
        f"/api/operator/tasks/{task_id}/comments",
        json={"message": "Документ приложен в карточке."},
    )
    assert client_comment.status_code == 201
    assert client_comment.json()["author_role"] == "client"

    operator_id = _promote_current_user()
    returned = auth_client.patch(
        f"/api/operator/tasks/{task_id}", json={"status": "waiting_client"}
    )
    assert returned.status_code == 200
    assert returned.json()["returned_at"] is not None

    operator_comment = auth_client.post(
        f"/api/operator/tasks/{task_id}/comments",
        json={"message": "Уточните область действия документа."},
    )
    assert operator_comment.status_code == 201
    assert operator_comment.json()["author_role"] == "operator"
    comments = auth_client.get(f"/api/operator/tasks/{task_id}/comments").json()
    assert [comment["author_role"] for comment in comments] == ["client", "operator"]

    assigned = auth_client.patch(
        "/api/operator/tasks/bulk-assign",
        json={"ids": [task_id, second.json()["id"]], "assignee_id": operator_id},
    )
    assert assigned.status_code == 200
    assert assigned.json()["updated"] == 2

    sorted_tasks = auth_client.get(
        "/api/operator/tasks", params={"sort_by": "priority", "sort_order": "desc"}
    )
    assert sorted_tasks.status_code == 200
    assert sorted_tasks.json()["items"][0]["priority"] == 3

    history = auth_client.get(f"/api/operator/tasks/{task_id}/history")
    assert history.status_code == 200
    actions = {event["action"] for event in history.json()}
    assert "operator_task.commented" in actions
    assert "operator_task.assigned" in actions


def test_task_comments_are_tenant_isolated(auth_client, client) -> None:
    task_id = auth_client.post(
        "/api/operator/tasks", json={"title": "Приватная задача"}
    ).json()["id"]

    client.post(
        "/api/auth/register",
        json={
            "email": "other-comments@test.ru",
            "password": "password",
            "full_name": "Другой",
            "client_name": "Другой клиент",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "other-comments@test.ru", "password": "password"},
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    assert client.get(f"/api/operator/tasks/{task_id}/comments").status_code == 404
    assert client.post(
        f"/api/operator/tasks/{task_id}/comments", json={"message": "Чужой комментарий"}
    ).status_code == 404
