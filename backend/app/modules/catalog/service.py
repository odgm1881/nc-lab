"""Сценарии каталога: CRUD, валидация, готовность к публикации, вариации.

Здесь оркестрация и транзакции. Доменные правила берём из модуля validation
(реестр правил), логику вариаций — из модуля variations. Каталог не лезет в чужие
таблицы: он владеет только `cards`.

Чтобы уменьшить ручную работу:
- карточки автоматически валидируются сразу после импорта и построения вариаций;
- есть массовая валидация всех не отмеченных готовыми карточек (validate_all);
- каталог группируется по модели (name) — вариации одного товара не смешиваются.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.modules.catalog import repository as repo
from app.modules.catalog.models import (
    STATUS_DRAFT,
    STATUS_ERROR,
    STATUS_PUBLISHED,
    STATUS_VALID,
    Card,
)
from app.modules.catalog.schemas import (
    BuildFromVariationsIn,
    BuildFromVariationsOut,
    CardCreateIn,
    CardListOut,
    CardOut,
    CardUpdateIn,
    CardValidateOut,
    ModelGroupOut,
    ModelsOut,
    ValidateAllOut,
)
from app.modules.gtin.domain import normalize_gtin
from app.modules.validation.domain.registry import run_validation
from app.modules.validation.domain.result import CardView, ValidationContext, ValidationResult
from app.modules.validation.service import result_to_schema
from app.modules.variations.domain import (
    VariationAxes,
    build_variations,
    variation_sku,
)


def _to_out(card: Card) -> CardOut:
    return CardOut.model_validate(card)


def _require(db: Session, client_id: str, card_id: str) -> Card:
    card = repo.get(db, client_id, card_id)
    if card is None:
        raise NotFoundError("Карточка не найдена.")
    return card


# --- валидация: переиспользуемые помощники (без commit) ---


def _card_view(card: Card) -> CardView:
    return CardView(
        id=card.id,
        client_id=card.client_id,
        category_code=card.category_code,
        gtin=card.gtin,
        attributes=card.attributes or {},
        rd_data=card.rd_data or {},
    )


def _store_result(card: Card, result: ValidationResult) -> None:
    card.status = STATUS_VALID if result.is_valid else STATUS_ERROR
    card.validation_issues = [
        {"code": i.code, "severity": i.severity.value, "message": i.message, "field": i.field}
        for i in result.issues
    ]


def _validate_one(db: Session, client_id: str, card: Card) -> ValidationResult:
    context = ValidationContext(gtin_index=repo.gtin_index(db, client_id, exclude_id=card.id))
    result = run_validation(_card_view(card), context)
    _store_result(card, result)
    return result


def _validate_many(db: Session, client_id: str, cards: list[Card]) -> None:
    """Прогнать список карточек через правила за один проход. Без commit.

    Индекс GTIN строится один раз. Правило уникальности сравнивает владельца GTIN с
    id самой карточки, поэтому общий индекс подходит для всех карточек сразу.
    """
    if not cards:
        return
    index = repo.gtin_index(db, client_id)
    for card in cards:
        result = run_validation(_card_view(card), ValidationContext(gtin_index=index))
        _store_result(card, result)


def _status_counts(db: Session, client_id: str) -> dict[str, int]:
    return repo.status_counts(db, client_id)


# --- CRUD ---


def create_card(db: Session, client_id: str, data: CardCreateIn) -> CardOut:
    card = Card(
        client_id=client_id,
        name=data.name,
        vendor_code=data.vendor_code,
        category_code=data.category_code,
        gtin=normalize_gtin(data.gtin) or None,
        attributes=data.attributes or {},
        rd_data=data.rd_data or {},
        status=STATUS_DRAFT,
    )
    try:
        repo.add(db, card)  # flush может бросить IntegrityError на дубликате GTIN
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("GTIN уже привязан к другой карточке.") from exc
    db.refresh(card)
    return _to_out(card)


def get_card(db: Session, client_id: str, card_id: str) -> CardOut:
    return _to_out(_require(db, client_id, card_id))


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
) -> CardListOut:
    items, total = repo.list_cards(
        db,
        client_id,
        status=status,
        category_code=category_code,
        name=name,
        search=search,
        limit=limit,
        offset=offset,
    )
    return CardListOut(items=[_to_out(c) for c in items], total=total)


def update_card(db: Session, client_id: str, card_id: str, data: CardUpdateIn) -> CardOut:
    card = _require(db, client_id, card_id)
    if card.status == STATUS_PUBLISHED:
        raise ConflictError("Карточку, готовую к публикации, нельзя редактировать.")

    if data.name is not None:
        card.name = data.name
    if data.vendor_code is not None:
        card.vendor_code = data.vendor_code
    if data.category_code is not None:
        card.category_code = data.category_code
    if data.gtin is not None:
        card.gtin = normalize_gtin(data.gtin) or None
    if data.attributes is not None:
        card.attributes = data.attributes
    if data.rd_data is not None:
        card.rd_data = data.rd_data

    # Любое изменение возвращает карточку в черновик — нужна повторная валидация.
    card.status = STATUS_DRAFT
    card.validation_issues = []
    _commit(db, "GTIN уже привязан к другой карточке.")
    db.refresh(card)
    return _to_out(card)


def delete_card(db: Session, client_id: str, card_id: str) -> None:
    card = _require(db, client_id, card_id)
    repo.delete(db, card)
    db.commit()


def validate_card(db: Session, client_id: str, card_id: str) -> CardValidateOut:
    """Прогнать одну карточку через ядро правил и обновить статус valid/error."""
    card = _require(db, client_id, card_id)
    result = _validate_one(db, client_id, card)
    db.commit()
    db.refresh(card)
    return CardValidateOut(card=_to_out(card), result=result_to_schema(result))


def validate_all(db: Session, client_id: str) -> ValidateAllOut:
    """Массовая валидация всех карточек, ещё не отмеченных готовыми."""
    cards = repo.list_unpublished(db, client_id)
    _validate_many(db, client_id, cards)
    db.commit()
    counts = _status_counts(db, client_id)
    return ValidateAllOut(
        validated=len(cards),
        valid=counts.get(STATUS_VALID, 0),
        error=counts.get(STATUS_ERROR, 0),
    )


def mark_ready(db: Session, client_id: str, card_id: str) -> CardOut:
    """Отметить внутреннюю готовность; внешнего обмена с НК здесь нет."""
    card = _require(db, client_id, card_id)
    if card.status != STATUS_VALID:
        raise DomainError(
            "Готовой к публикации можно отметить только валидную карточку.",
            code="NOT_VALID",
        )
    card.status = STATUS_PUBLISHED
    db.commit()
    db.refresh(card)
    return _to_out(card)


def publish_card(db: Session, client_id: str, card_id: str) -> CardOut:
    """Обратная совместимость старого API; действие только внутреннее."""
    return mark_ready(db, client_id, card_id)


def build_from_variations(
    db: Session, client_id: str, data: BuildFromVariationsIn
) -> BuildFromVariationsOut:
    """Создать по одной карточке на каждую комбинацию вариаций и сразу провалидировать.

    Правило легпрома: каждая комбинация цвет×размер×пол×комплектность — отдельная
    карточка. Автовалидация сразу показывает, чего не хватает (обычно GTIN), без
    ручного клика по каждой карточке.
    """
    axes = VariationAxes(
        colors=data.colors,
        sizes=data.sizes,
        genders=data.genders,
        completeness=data.completeness,
    )
    variations = build_variations(axes)
    cards: list[Card] = []
    for v in variations:
        attributes = {**(data.common_attributes or {}), **v.as_attributes()}
        card = Card(
            client_id=client_id,
            name=data.name,
            vendor_code=variation_sku(data.base_vendor_code, v),
            category_code=data.category_code,
            gtin=None,
            attributes=attributes,
            rd_data=data.rd_data or {},
            status=STATUS_DRAFT,
        )
        repo.add(db, card)
        cards.append(card)
    _validate_many(db, client_id, cards)  # автовалидация
    db.commit()
    for c in cards:
        db.refresh(c)
    return BuildFromVariationsOut(created=len(cards), cards=[_to_out(c) for c in cards])


def create_cards_bulk(db: Session, client_id: str, payloads: list[CardCreateIn]) -> int:
    """Массовое создание карточек (для импорта) с автовалидацией. Без commit.

    Транзакцией управляет вызывающий сценарий. Чтобы не нарушить правило
    «1 GTIN = 1 карточка», повторяющиеся GTIN (внутри пачки или уже существующие)
    сбрасываются в NULL — такая карточка помечается ошибкой (нет GTIN), и оператор
    видит это сразу, без ручной валидации.
    """
    seen: set[str] = set(repo.gtin_index(db, client_id).keys())
    cards: list[Card] = []
    for data in payloads:
        gtin = normalize_gtin(data.gtin) or None
        if gtin and gtin in seen:
            gtin = None  # дубликат — оставляем без GTIN, разрешит оператор
        if gtin:
            seen.add(gtin)
        card = Card(
            client_id=client_id,
            name=data.name,
            vendor_code=data.vendor_code,
            category_code=data.category_code,
            gtin=gtin,
            attributes=data.attributes or {},
            rd_data=data.rd_data or {},
            status=STATUS_DRAFT,
        )
        repo.add(db, card)
        cards.append(card)
    _validate_many(db, client_id, cards)  # автовалидация сразу после импорта
    return len(cards)


# --- модели (группировка каталога) ---


def list_models(db: Session, client_id: str, *, search: str | None = None) -> ModelsOut:
    """Сгруппировать карточки по модели (name): вариации одного товара вместе."""
    rows = repo.model_status_rows(db, client_id, search=search)
    groups: dict[str, ModelGroupOut] = {}
    for name, category_code, status, n in rows:
        key = name or "—"
        g = groups.get(key)
        if g is None:
            g = ModelGroupOut(name=key, category_code=category_code, total=0, counts={})
            groups[key] = g
        if category_code and not g.category_code:
            g.category_code = category_code
        g.total += n
        g.counts[status] = g.counts.get(status, 0) + n
    items = sorted(groups.values(), key=lambda x: x.name.lower())
    return ModelsOut(items=items)


def _commit(db: Session, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(conflict_message) from exc
