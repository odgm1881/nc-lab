from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.catalog.models import STATUS_PUBLISHED, Card
from app.modules.nk_exchange.domain import SCHEMA_VERSION, adapter_for
from app.modules.nk_exchange.models import NkExchange
from app.modules.nk_exchange.schemas import ExchangeCreateIn, ExchangeListOut, ExchangeOut


def _require_card(db: Session, client_id: str, card_id: str) -> Card:
    card = db.get(Card, card_id)
    if card is None or card.client_id != client_id:
        raise NotFoundError("Карточка не найдена.")
    if card.status != STATUS_PUBLISHED:
        raise DomainError("Для обмена карточка должна быть готова к публикации.")
    return card


def _require_exchange(db: Session, client_id: str, exchange_id: str) -> NkExchange:
    item = db.get(NkExchange, exchange_id)
    if item is None or item.client_id != client_id:
        raise NotFoundError("Операция обмена не найдена.")
    return item


def _payload(card: Card) -> dict:
    """Нейтральный контракт: официальный mapping добавляется отдельным адаптером."""
    return {
        "schema_version": SCHEMA_VERSION,
        "card_id": card.id,
        "name": card.name,
        "vendor_code": card.vendor_code,
        "category_code": card.category_code,
        "gtin": card.gtin,
        "attributes": card.attributes or {},
        "rd_data": card.rd_data or {},
        "packaging": card.packaging or {},
        "ruleset_version": card.ruleset_version,
        "reference_data_version": card.reference_data_version,
    }


def _execute(item: NkExchange) -> None:
    item.attempts += 1
    result = adapter_for(item.mode).send(item.request_payload, item.idempotency_key)
    item.status = result.status
    item.response_payload = result.response
    item.error = result.error


def create(
    db: Session, client_id: str, data: ExchangeCreateIn, actor_id: str | None
) -> ExchangeOut:
    card = _require_card(db, client_id, data.card_id)
    key = data.idempotency_key or f"card-{card.id}-{uuid4().hex}"
    existing = db.scalar(
        select(NkExchange).where(
            NkExchange.client_id == client_id, NkExchange.idempotency_key == key
        )
    )
    if existing:
        if existing.card_id != card.id or existing.mode != data.mode:
            raise ConflictError("Ключ идемпотентности уже использован для другого запроса.")
        return ExchangeOut.model_validate(existing)

    item = NkExchange(
        client_id=client_id,
        card_id=card.id,
        idempotency_key=key,
        mode=data.mode,
        status="pending",
        request_payload=_payload(card),
        response_payload={},
        attempts=0,
    )
    db.add(item)
    _execute(item)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="nk_exchange.created",
        entity_type="nk_exchange",
        entity_id=item.id,
        details={"card_id": card.id, "mode": item.mode, "status": item.status},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Операция с таким ключом уже существует.") from exc
    db.refresh(item)
    return ExchangeOut.model_validate(item)


def get(db: Session, client_id: str, exchange_id: str) -> ExchangeOut:
    return ExchangeOut.model_validate(_require_exchange(db, client_id, exchange_id))


def list_items(db: Session, client_id: str, limit: int, offset: int) -> ExchangeListOut:
    total = db.scalar(
        select(func.count()).select_from(NkExchange).where(NkExchange.client_id == client_id)
    ) or 0
    stmt = (
        select(NkExchange)
        .where(NkExchange.client_id == client_id)
        .order_by(NkExchange.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return ExchangeListOut(items=list(db.scalars(stmt)), total=total)


def retry(db: Session, client_id: str, exchange_id: str, actor_id: str | None) -> ExchangeOut:
    item = _require_exchange(db, client_id, exchange_id)
    if item.status not in {"failed", "prepared"}:
        raise ConflictError("Повтор доступен только для failed или prepared операции.")
    _execute(item)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="nk_exchange.retried",
        entity_type="nk_exchange",
        entity_id=item.id,
        details={"attempts": item.attempts, "status": item.status},
    )
    db.commit()
    db.refresh(item)
    return ExchangeOut.model_validate(item)


def export_payload(db: Session, client_id: str, exchange_id: str) -> bytes:
    item = _require_exchange(db, client_id, exchange_id)
    return (json.dumps(item.request_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
