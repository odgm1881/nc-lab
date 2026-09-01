from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user, require_editor
from app.modules.auth.models import User
from app.modules.pilots import service
from app.modules.pilots.schemas import (
    PilotCardsIn,
    PilotCreateIn,
    PilotDetailOut,
    PilotListOut,
    PilotUpdateIn,
)

router = APIRouter()


def _client_id(user: User) -> str:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return user.client_id


@router.get("", response_model=PilotListOut)
def list_pilots(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> PilotListOut:
    return service.list_pilots(db, _client_id(user))


@router.post("", response_model=PilotDetailOut, status_code=201)
def create_pilot(
    data: PilotCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> PilotDetailOut:
    return service.create_pilot(db, _client_id(user), data, user.id)


@router.get("/{pilot_id}", response_model=PilotDetailOut)
def get_pilot(
    pilot_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PilotDetailOut:
    return service.get_pilot(db, _client_id(user), pilot_id)


@router.patch("/{pilot_id}", response_model=PilotDetailOut)
def update_pilot(
    pilot_id: str,
    data: PilotUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> PilotDetailOut:
    return service.update_pilot(db, _client_id(user), pilot_id, data, user.id)


@router.post("/{pilot_id}/cards", response_model=PilotDetailOut)
def add_cards(
    pilot_id: str,
    data: PilotCardsIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> PilotDetailOut:
    return service.add_cards(db, _client_id(user), pilot_id, data.card_ids, user.id)


@router.delete("/{pilot_id}/cards/{card_id}", response_model=PilotDetailOut)
def remove_card(
    pilot_id: str,
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> PilotDetailOut:
    return service.remove_card(db, _client_id(user), pilot_id, card_id, user.id)


@router.post("/{pilot_id}/start", response_model=PilotDetailOut)
def start_pilot(
    pilot_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> PilotDetailOut:
    return service.start_pilot(db, _client_id(user), pilot_id, user.id)


@router.post("/{pilot_id}/complete", response_model=PilotDetailOut)
def complete_pilot(
    pilot_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> PilotDetailOut:
    return service.complete_pilot(db, _client_id(user), pilot_id, user.id)


@router.get("/{pilot_id}/report.csv")
def report(
    pilot_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    content = service.export_report(db, _client_id(user), pilot_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pilot-report.csv"'},
    )
