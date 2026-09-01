"""API-слой консоли оператора. Только HTTP.

Список и управление задачами — для операторов каталога. Создание задачи может
инициировать и клиент (эскалация спорной карточки).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.audit.schemas import AuditEventOut
from app.modules.auth.dependencies import get_current_user, require_operator
from app.modules.auth.models import User
from app.modules.operator import service
from app.modules.operator.schemas import (
    TaskBulkAssignIn,
    TaskBulkAssignOut,
    TaskCommentCreateIn,
    TaskCommentOut,
    TaskCreateIn,
    TaskListOut,
    TaskOut,
    TaskUpdateIn,
)

router = APIRouter()


@router.get("/tasks", response_model=TaskListOut)
def list_tasks(
    status: str | None = None,
    client_id: str | None = None,
    assignee_id: str | None = None,
    overdue: bool | None = None,
    sort_by: str = "priority",
    sort_order: str = "desc",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> TaskListOut:
    return service.list_tasks(
        db,
        status=status,
        client_id=client_id,
        assignee_id=assignee_id,
        overdue=overdue,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    data: TaskCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskOut:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return service.create_task(db, user.client_id, data, user.id)


@router.get("/my-tasks", response_model=TaskListOut)
def my_tasks(
    card_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskListOut:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return service.list_client_tasks(db, user.client_id, card_id=card_id)


@router.patch("/tasks/bulk-assign", response_model=TaskBulkAssignOut)
def bulk_assign(
    data: TaskBulkAssignIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> TaskBulkAssignOut:
    return service.bulk_assign(db, data.ids, data.assignee_id, user.id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    data: TaskUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> TaskOut:
    return service.update_task(db, task_id, data, user.id)


@router.get("/tasks/{task_id}/comments", response_model=list[TaskCommentOut])
def list_comments(
    task_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TaskCommentOut]:
    return service.list_comments(db, task_id, user)


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentOut, status_code=201)
def add_comment(
    task_id: str,
    data: TaskCommentCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskCommentOut:
    return service.add_comment(db, task_id, data.message, user)


@router.get("/tasks/{task_id}/history", response_model=list[AuditEventOut])
def task_history(
    task_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditEventOut]:
    return service.task_history(db, task_id, user)
