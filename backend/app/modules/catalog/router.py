"""API-слой каталога. Только HTTP."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.catalog import service
from app.modules.catalog.schemas import (
    BuildFromVariationsIn,
    BuildFromVariationsOut,
    CardCreateIn,
    CardListOut,
    CardOut,
    CardUpdateIn,
    CardValidateOut,
    ModelsOut,
    ValidateAllOut,
)

router = APIRouter()


def _client_id(user: User) -> str:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return user.client_id


@router.get("", response_model=CardListOut)
def list_cards(
    status: str | None = None,
    category_code: str | None = None,
    name: str | None = None,
    search: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardListOut:
    return service.list_cards(
        db,
        _client_id(user),
        status=status,
        category_code=category_code,
        name=name,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/models", response_model=ModelsOut)
def list_models(
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ModelsOut:
    """Каталог, сгруппированный по модели (товару): вариации не смешиваются."""
    return service.list_models(db, _client_id(user), search=search)


@router.post("/validate-all", response_model=ValidateAllOut)
def validate_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ValidateAllOut:
    """Провалидировать все карточки, ещё не отмеченные готовыми."""
    return service.validate_all(db, _client_id(user))


@router.post("", response_model=CardOut, status_code=201)
def create_card(
    data: CardCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardOut:
    return service.create_card(db, _client_id(user), data)


@router.post("/build-from-variations", response_model=BuildFromVariationsOut, status_code=201)
def build_from_variations(
    data: BuildFromVariationsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BuildFromVariationsOut:
    return service.build_from_variations(db, _client_id(user), data)


@router.get("/{card_id}", response_model=CardOut)
def get_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardOut:
    return service.get_card(db, _client_id(user), card_id)


@router.patch("/{card_id}", response_model=CardOut)
def update_card(
    card_id: str,
    data: CardUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardOut:
    return service.update_card(db, _client_id(user), card_id, data)


@router.delete("/{card_id}", status_code=204)
def delete_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    service.delete_card(db, _client_id(user), card_id)


@router.post("/{card_id}/validate", response_model=CardValidateOut)
def validate_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardValidateOut:
    return service.validate_card(db, _client_id(user), card_id)


@router.post("/{card_id}/ready", response_model=CardOut)
def mark_ready(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardOut:
    """Отметить карточку готовой к публикации без внешнего обмена."""
    return service.mark_ready(db, _client_id(user), card_id)


@router.post("/{card_id}/publish", response_model=CardOut, include_in_schema=False)
def publish_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardOut:
    """Устаревший маршрут для совместимости; внешней публикации не выполняет."""
    return service.publish_card(db, _client_id(user), card_id)
