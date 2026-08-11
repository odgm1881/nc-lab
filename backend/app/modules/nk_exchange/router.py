from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.nk_exchange import service
from app.modules.nk_exchange.schemas import ExchangeCreateIn, ExchangeListOut, ExchangeOut

router = APIRouter()


def _client_id(user: User) -> str:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return user.client_id


@router.post("/exchanges", response_model=ExchangeOut, status_code=201)
def create_exchange(
    data: ExchangeCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExchangeOut:
    return service.create(db, _client_id(user), data, user.id)


@router.get("/exchanges", response_model=ExchangeListOut)
def list_exchanges(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExchangeListOut:
    return service.list_items(db, _client_id(user), limit, offset)


@router.get("/exchanges/{exchange_id}", response_model=ExchangeOut)
def get_exchange(
    exchange_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExchangeOut:
    return service.get(db, _client_id(user), exchange_id)


@router.post("/exchanges/{exchange_id}/retry", response_model=ExchangeOut)
def retry_exchange(
    exchange_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExchangeOut:
    return service.retry(db, _client_id(user), exchange_id, user.id)


@router.get("/exchanges/{exchange_id}/payload")
def download_payload(
    exchange_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    content = service.export_payload(db, _client_id(user), exchange_id)
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="nk-{exchange_id}.json"'},
    )
