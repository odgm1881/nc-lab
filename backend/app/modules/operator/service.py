"""Сценарии консоли оператора: очередь задач по спорным карточкам."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import User
from app.modules.catalog import service as catalog_service
from app.modules.operator.models import (
    STATUS_IN_PROGRESS,
    STATUS_OPEN,
    STATUS_RESOLVED,
    STATUS_WAITING_CLIENT,
    OperatorTask,
    OperatorTaskComment,
)
from app.modules.operator.schemas import (
    TaskBulkAssignOut,
    TaskCommentOut,
    TaskCreateIn,
    TaskListOut,
    TaskOut,
    TaskUpdateIn,
)

_ALLOWED_STATUSES = {
    STATUS_OPEN,
    STATUS_IN_PROGRESS,
    STATUS_WAITING_CLIENT,
    STATUS_RESOLVED,
}
_ALLOWED_CATEGORIES = {"attributes", "gtin", "rd", "category", "integration", "other"}
_SORT_COLUMNS = {
    "priority": OperatorTask.priority,
    "due_at": OperatorTask.due_at,
    "created_at": OperatorTask.created_at,
}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _to_out(task: OperatorTask, now: datetime | None = None) -> TaskOut:
    current = now or datetime.now(UTC)
    overdue = bool(
        task.due_at
        and task.status != STATUS_RESOLVED
        and _utc(task.due_at) < current
    )
    return TaskOut.model_validate(task).model_copy(update={"is_overdue": overdue})


def create_task(
    db: Session, client_id: str, data: TaskCreateIn, actor_id: str | None = None
) -> TaskOut:
    # Проверяем владение через публичный сервис каталога, не обращаясь к его таблице.
    if data.card_id:
        catalog_service.get_card(db, client_id, data.card_id)
    if data.category not in _ALLOWED_CATEGORIES:
        raise DomainError("Недопустимая категория обращения.")
    task = OperatorTask(
        client_id=client_id,
        card_id=data.card_id,
        title=data.title,
        category=data.category,
        note=data.note,
        escalation_reason=data.escalation_reason,
        due_at=data.due_at,
        priority=data.priority,
        status=STATUS_OPEN,
    )
    db.add(task)
    db.flush()
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="operator_task.created",
        entity_type="operator_task",
        entity_id=task.id,
        after=audit_service.snapshot(task),
    )
    db.commit()
    db.refresh(task)
    return _to_out(task)


def list_tasks(
    db: Session,
    *,
    status: str | None = None,
    client_id: str | None = None,
    assignee_id: str | None = None,
    overdue: bool | None = None,
    sort_by: str = "priority",
    sort_order: str = "desc",
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
    if assignee_id:
        stmt = stmt.where(OperatorTask.assignee_id == assignee_id)
        count_stmt = count_stmt.where(OperatorTask.assignee_id == assignee_id)
    if overdue:
        now = datetime.now(UTC)
        overdue_filter = (
            OperatorTask.due_at.is_not(None),
            OperatorTask.due_at < now,
            OperatorTask.status != STATUS_RESOLVED,
        )
        stmt = stmt.where(*overdue_filter)
        count_stmt = count_stmt.where(*overdue_filter)

    total = db.scalar(count_stmt) or 0
    if sort_by not in _SORT_COLUMNS:
        raise DomainError("Недопустимое поле сортировки задач.")
    if sort_order not in {"asc", "desc"}:
        raise DomainError("Недопустимое направление сортировки задач.")
    column = _SORT_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()
    stmt = stmt.order_by(order, OperatorTask.created_at.asc()).limit(limit).offset(offset)
    items = list(db.scalars(stmt))
    now = datetime.now(UTC)
    return TaskListOut(items=[_to_out(t, now) for t in items], total=total)


def update_task(
    db: Session, task_id: str, data: TaskUpdateIn, actor_id: str | None = None
) -> TaskOut:
    task = db.get(OperatorTask, task_id)
    if task is None:
        raise NotFoundError("Задача не найдена.")
    before = audit_service.snapshot(task)
    if data.status is not None:
        if data.status not in _ALLOWED_STATUSES:
            raise DomainError(f"Недопустимый статус задачи: {data.status}")
        now = datetime.now(UTC)
        if data.status == STATUS_IN_PROGRESS and task.started_at is None:
            task.started_at = now
        if data.status == STATUS_WAITING_CLIENT:
            task.returned_at = now
        if data.status == STATUS_RESOLVED:
            resolution = (
                data.resolution if "resolution" in data.model_fields_set else task.resolution
            )
            if not resolution or not resolution.strip():
                raise DomainError(
                    "Для завершения задачи укажите результат решения.",
                    code="TASK_RESOLUTION_REQUIRED",
                )
            task.resolution = resolution.strip()
            task.started_at = task.started_at or now
            task.resolved_at = now
        elif task.status == STATUS_RESOLVED:
            task.resolved_at = None
            if "resolution" not in data.model_fields_set:
                task.resolution = None
        task.status = data.status
    if data.priority is not None:
        task.priority = data.priority
    if data.category is not None:
        if data.category not in _ALLOWED_CATEGORIES:
            raise DomainError("Недопустимая категория обращения.")
        task.category = data.category
    if "note" in data.model_fields_set:
        task.note = data.note
    if "assignee_id" in data.model_fields_set:
        task.assignee_id = data.assignee_id
    if "escalation_reason" in data.model_fields_set:
        task.escalation_reason = data.escalation_reason
    if "resolution" in data.model_fields_set and data.status != STATUS_RESOLVED:
        task.resolution = data.resolution
    if "due_at" in data.model_fields_set:
        task.due_at = data.due_at
    audit_service.record(
        db,
        client_id=task.client_id,
        actor_id=actor_id,
        action="operator_task.updated",
        entity_type="operator_task",
        entity_id=task.id,
        before=before,
        after=audit_service.snapshot(task),
    )
    db.commit()
    db.refresh(task)
    return _to_out(task)


def _task_for_user(db: Session, task_id: str, user: User) -> OperatorTask:
    task = db.get(OperatorTask, task_id)
    if task is None:
        raise NotFoundError("Задача не найдена.")
    if user.role not in {"operator", "admin"} and task.client_id != user.client_id:
        raise NotFoundError("Задача не найдена.")
    return task


def list_client_tasks(
    db: Session,
    client_id: str,
    *,
    card_id: str | None = None,
) -> TaskListOut:
    stmt = select(OperatorTask).where(OperatorTask.client_id == client_id)
    count_stmt = select(func.count()).select_from(OperatorTask).where(
        OperatorTask.client_id == client_id
    )
    if card_id:
        stmt = stmt.where(OperatorTask.card_id == card_id)
        count_stmt = count_stmt.where(OperatorTask.card_id == card_id)
    items = list(db.scalars(stmt.order_by(OperatorTask.created_at.desc())))
    total = db.scalar(count_stmt) or 0
    now = datetime.now(UTC)
    return TaskListOut(items=[_to_out(task, now) for task in items], total=total)


def bulk_assign(
    db: Session,
    ids: list[str],
    assignee_id: str,
    actor_id: str,
) -> TaskBulkAssignOut:
    unique_ids = list(dict.fromkeys(ids))
    tasks = list(db.scalars(select(OperatorTask).where(OperatorTask.id.in_(unique_ids))))
    if len(tasks) != len(unique_ids):
        raise NotFoundError("Одна или несколько задач не найдены.")
    for task in tasks:
        before = audit_service.snapshot(task)
        task.assignee_id = assignee_id
        if task.status in {STATUS_OPEN, STATUS_WAITING_CLIENT}:
            task.status = STATUS_IN_PROGRESS
            task.started_at = task.started_at or datetime.now(UTC)
        audit_service.record(
            db,
            client_id=task.client_id,
            actor_id=actor_id,
            action="operator_task.assigned",
            entity_type="operator_task",
            entity_id=task.id,
            before=before,
            after=audit_service.snapshot(task),
        )
    db.commit()
    return TaskBulkAssignOut(updated=len(tasks))


def list_comments(db: Session, task_id: str, user: User) -> list[TaskCommentOut]:
    task = _task_for_user(db, task_id, user)
    comments = list(
        db.scalars(
            select(OperatorTaskComment)
            .where(
                OperatorTaskComment.task_id == task.id,
                OperatorTaskComment.client_id == task.client_id,
            )
            .order_by(OperatorTaskComment.created_at.asc())
        )
    )
    return [TaskCommentOut.model_validate(comment) for comment in comments]


def add_comment(
    db: Session, task_id: str, message: str, user: User
) -> TaskCommentOut:
    task = _task_for_user(db, task_id, user)
    clean = message.strip()
    if not clean:
        raise DomainError("Комментарий не может быть пустым.")
    comment = OperatorTaskComment(
        client_id=task.client_id,
        task_id=task.id,
        author_id=user.id,
        author_role=user.role,
        author_name=user.full_name or user.email,
        message=clean,
    )
    db.add(comment)
    db.flush()
    audit_service.record(
        db,
        client_id=task.client_id,
        actor_id=user.id,
        action="operator_task.commented",
        entity_type="operator_task",
        entity_id=task.id,
        details={"comment_id": comment.id, "author_role": user.role},
    )
    db.commit()
    db.refresh(comment)
    return TaskCommentOut.model_validate(comment)


def task_history(db: Session, task_id: str, user: User) -> list[AuditEvent]:
    task = _task_for_user(db, task_id, user)
    return audit_service.history(db, task.client_id, "operator_task", task.id)
