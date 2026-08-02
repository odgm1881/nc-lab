"""Доступ к данным каталога карточек."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import STATUS_PUBLISHED, Card
from app.modules.gtin.domain import normalize_gtin


def get(db: Session, client_id: str, card_id: str) -> Card | None:
    card = db.get(Card, card_id)
    if card is None or card.client_id != client_id:
        return None
    return card


def list_cards(
    db: Session,
    client_id: str,
    *,
    status: str | None = None,
    category_code: str | None = None,
    name: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Card], int]:
    stmt = select(Card).where(Card.client_id == client_id)
    count_stmt = select(func.count()).select_from(Card).where(Card.client_id == client_id)

    if status:
        stmt = stmt.where(Card.status == status)
        count_stmt = count_stmt.where(Card.status == status)
    if category_code:
        stmt = stmt.where(Card.category_code == category_code)
        count_stmt = count_stmt.where(Card.category_code == category_code)
    if name:
        stmt = stmt.where(Card.name == name)
        count_stmt = count_stmt.where(Card.name == name)
    if search:
        like = f"%{search}%"
        cond = or_(Card.name.ilike(like), Card.vendor_code.ilike(like), Card.gtin.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(Card.name.asc(), Card.vendor_code.asc()).limit(limit).offset(offset)
    return list(db.scalars(stmt)), total


def list_unpublished(db: Session, client_id: str) -> list[Card]:
    """Все карточки клиента, кроме отмеченных готовыми — для массовой валидации."""
    stmt = select(Card).where(Card.client_id == client_id, Card.status != STATUS_PUBLISHED)
    return list(db.scalars(stmt))


def list_by_ids(db: Session, client_id: str, ids: list[str]) -> list[Card]:
    if not ids:
        return []
    stmt = select(Card).where(Card.client_id == client_id, Card.id.in_(ids))
    return list(db.scalars(stmt))


def status_counts(db: Session, client_id: str) -> dict[str, int]:
    stmt = (
        select(Card.status, func.count())
        .where(Card.client_id == client_id)
        .group_by(Card.status)
    )
    return {status: n for status, n in db.execute(stmt)}


def model_status_rows(
    db: Session, client_id: str, *, search: str | None = None
) -> list[tuple[str | None, str | None, str, int]]:
    """Строки (name, category_code, status, count) для группировки по модели."""
    stmt = select(Card.name, Card.category_code, Card.status, func.count()).where(
        Card.client_id == client_id
    )
    if search:
        stmt = stmt.where(Card.name.ilike(f"%{search}%"))
    stmt = stmt.group_by(Card.name, Card.category_code, Card.status)
    return [tuple(row) for row in db.execute(stmt)]


def add(db: Session, card: Card) -> Card:
    db.add(card)
    db.flush()
    return card


def delete(db: Session, card: Card) -> None:
    db.delete(card)


def gtin_index(db: Session, client_id: str, exclude_id: str | None = None) -> dict[str, str]:
    """Карта «нормализованный GTIN -> id карточки» для клиента.

    Нужна правилу уникальности GTIN. Пустые GTIN пропускаем.
    """
    stmt = select(Card.id, Card.gtin).where(Card.client_id == client_id, Card.gtin.is_not(None))
    index: dict[str, str] = {}
    for card_id, gtin in db.execute(stmt):
        key = normalize_gtin(gtin)
        if key and (exclude_id is None or card_id != exclude_id):
            index[key] = card_id
    return index
