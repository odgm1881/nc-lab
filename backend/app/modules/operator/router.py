"""API-слой консоли оператора. Только HTTP.

Список и управление задачами — для операторов каталога. Создание задачи может
инициировать и клиент (эскалация спорной карточки).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user, require_operator
from app.modules.auth.models import User
from app.modules.operator import service
from app.modules.operator.schemas import (
    TaskCreateIn,
    TaskListOut,
    TaskOut,
    TaskUpdateIn,
)

router = APIRouter()


@router.get("/tasks", response_model=TaskListOut)
def list_tasks(
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> TaskListOut:
    return service.list_tasks(db, status=status, limit=limit, offset=offset)


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    data: TaskCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskOut:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return service.create_task(db, user.client_id, data, user.id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    data: TaskUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> TaskOut:
    return service.update_task(db, task_id, data, user.id)
