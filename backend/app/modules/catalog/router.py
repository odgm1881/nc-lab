"""API-слой каталога. Только HTTP."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.audit import service as audit_service
from app.modules.audit.schemas import AuditEventOut
from app.modules.auth.dependencies import get_current_user, require_editor
from app.modules.auth.models import User
from app.modules.catalog import service
from app.modules.catalog.schemas import (
    BuildFromVariationsIn,
    BuildFromVariationsOut,
    CardBulkUpdateIn,
    CardBulkUpdateOut,
    CardCreateIn,
    CardExportIn,
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
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
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
    user: User = Depends(require_editor),
) -> ValidateAllOut:
    """Провалидировать все карточки, ещё не отмеченные готовыми."""
    return service.validate_all(db, _client_id(user), user.id)


@router.patch("/bulk", response_model=CardBulkUpdateOut)
def bulk_update(
    data: CardBulkUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> CardBulkUpdateOut:
    return service.bulk_update(db, _client_id(user), data, user.id)


@router.post("/export")
def export_cards(
    data: CardExportIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    content = service.export_cards(db, _client_id(user), data, user.id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="cards-export.csv"'},
    )


@router.post("", response_model=CardOut, status_code=201)
def create_card(
    data: CardCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> CardOut:
    return service.create_card(db, _client_id(user), data, user.id)


@router.post("/build-from-variations", response_model=BuildFromVariationsOut, status_code=201)
def build_from_variations(
    data: BuildFromVariationsIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> BuildFromVariationsOut:
    return service.build_from_variations(db, _client_id(user), data, user.id)


@router.get("/{card_id}", response_model=CardOut)
def get_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardOut:
    return service.get_card(db, _client_id(user), card_id)


@router.get("/{card_id}/history", response_model=list[AuditEventOut])
def card_history(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditEventOut]:
    client_id = _client_id(user)
    service.get_card(db, client_id, card_id)
    return audit_service.history(db, client_id, "card", card_id)


@router.patch("/{card_id}", response_model=CardOut)
def update_card(
    card_id: str,
    data: CardUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> CardOut:
    return service.update_card(db, _client_id(user), card_id, data, user.id)


@router.delete("/{card_id}", status_code=204)
def delete_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> None:
    service.delete_card(db, _client_id(user), card_id, user.id)


@router.post("/{card_id}/validate", response_model=CardValidateOut)
def validate_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> CardValidateOut:
    return service.validate_card(db, _client_id(user), card_id, user.id)


@router.post("/{card_id}/ready", response_model=CardOut)
def mark_ready(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> CardOut:
    """Отметить карточку готовой к публикации без внешнего обмена."""
    return service.mark_ready(db, _client_id(user), card_id, user.id)


@router.post("/{card_id}/publish", response_model=CardOut, include_in_schema=False)
def publish_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> CardOut:
    """Устаревший маршрут для совместимости; внешней публикации не выполняет."""
    return service.publish_card(db, _client_id(user), card_id, user.id)
