"""Сценарии консоли оператора: очередь задач по спорным карточкам."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError
from app.modules.catalog import service as catalog_service
from app.modules.operator.models import (
    STATUS_IN_PROGRESS,
    STATUS_OPEN,
    STATUS_RESOLVED,
    OperatorTask,
)
from app.modules.operator.schemas import (
    TaskCreateIn,
    TaskListOut,
    TaskOut,
    TaskUpdateIn,
)

_ALLOWED_STATUSES = {STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_RESOLVED}


def create_task(db: Session, client_id: str, data: TaskCreateIn) -> TaskOut:
    # Проверяем владение через публичный сервис каталога, не обращаясь к его таблице.
    catalog_service.get_card(db, client_id, data.card_id)
    task = OperatorTask(
        client_id=client_id,
        card_id=data.card_id,
        title=data.title,
        note=data.note,
        priority=data.priority,
        status=STATUS_OPEN,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


def list_tasks(
    db: Session,
    *,
    status: str | None = None,
    client_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> TaskListOut:
    stmt = select(OperatorTask)
    count_stmt = select(func.count()).select_from(OperatorTask)
    if status:
        stmt = stmt.where(OperatorTask.status == status)
        count_stmt = count_stmt.where(OperatorTask.status == status)
    if client_id:
        stmt = stmt.where(OperatorTask.client_id == client_id)
        count_stmt = count_stmt.where(OperatorTask.client_id == client_id)

    total = db.scalar(count_stmt) or 0
    # Приоритетные и свежие — выше.
    stmt = (
        stmt.order_by(OperatorTask.priority.desc(), OperatorTask.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(stmt))
    return TaskListOut(items=[TaskOut.model_validate(t) for t in items], total=total)


def update_task(db: Session, task_id: str, data: TaskUpdateIn) -> TaskOut:
    task = db.get(OperatorTask, task_id)
    if task is None:
        raise NotFoundError("Задача не найдена.")
    if data.status is not None:
        if data.status not in _ALLOWED_STATUSES:
            raise DomainError(f"Недопустимый статус задачи: {data.status}")
        task.status = data.status
    if data.priority is not None:
        task.priority = data.priority
    if data.note is not None:
        task.note = data.note
    if data.assignee_id is not None:
        task.assignee_id = data.assignee_id
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)
