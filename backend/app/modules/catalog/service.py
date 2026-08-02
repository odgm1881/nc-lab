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

import csv
import io
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.modules.audit import service as audit_service
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
    CardBulkUpdateIn,
    CardBulkUpdateOut,
    CardCreateIn,
    CardExportIn,
    CardListOut,
    CardOut,
    CardUpdateIn,
    CardValidateOut,
    ModelGroupOut,
    ModelsOut,
    ValidateAllOut,
)
from app.modules.gtin.domain import normalize_gtin
from app.modules.validation.domain.registry import (
    REFERENCE_DATA_VERSION,
    RULESET_VERSION,
    run_validation,
)
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
    card.ruleset_version = RULESET_VERSION
    card.reference_data_version = REFERENCE_DATA_VERSION


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


def _csv_safe(value: object) -> object:
    """Не позволить таблицам выполнить пользовательское значение как формулу."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


# --- CRUD ---


def create_card(
    db: Session, client_id: str, data: CardCreateIn, actor_id: str | None = None
) -> CardOut:
    card = Card(
        client_id=client_id,
        name=data.name,
        vendor_code=data.vendor_code,
        category_code=data.category_code,
        gtin=normalize_gtin(data.gtin) or None,
        attributes=data.attributes or {},
        rd_data=data.rd_data or {},
        packaging=data.packaging or {},
        data_source=data.data_source,
        service_comment=data.service_comment,
        status=STATUS_DRAFT,
    )
    try:
        repo.add(db, card)  # flush может бросить IntegrityError на дубликате GTIN
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="card.created",
            entity_type="card",
            entity_id=card.id,
            after=audit_service.snapshot(card),
        )
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


def update_card(
    db: Session,
    client_id: str,
    card_id: str,
    data: CardUpdateIn,
    actor_id: str | None = None,
) -> CardOut:
    card = _require(db, client_id, card_id)
    if card.status == STATUS_PUBLISHED:
        raise ConflictError("Карточку, готовую к публикации, нельзя редактировать.")

    fields_set = data.model_fields_set
    if not fields_set:
        return _to_out(card)
    non_nullable = {"name", "vendor_code", "attributes", "rd_data", "packaging", "data_source"}
    invalid_nulls = sorted(
        field for field in fields_set & non_nullable if getattr(data, field) is None
    )
    if invalid_nulls:
        raise DomainError(f"Поля нельзя очищать: {', '.join(invalid_nulls)}")
    before = audit_service.snapshot(card)
    if "name" in fields_set and data.name is not None:
        card.name = data.name
    if "vendor_code" in fields_set and data.vendor_code is not None:
        card.vendor_code = data.vendor_code
    if "category_code" in fields_set:
        card.category_code = data.category_code
    if "gtin" in fields_set:
        card.gtin = normalize_gtin(data.gtin) or None
    if "attributes" in fields_set and data.attributes is not None:
        card.attributes = data.attributes
    if "rd_data" in fields_set and data.rd_data is not None:
        card.rd_data = data.rd_data
    if "packaging" in fields_set and data.packaging is not None:
        card.packaging = data.packaging
    if "data_source" in fields_set and data.data_source is not None:
        card.data_source = data.data_source
    if "service_comment" in fields_set:
        card.service_comment = data.service_comment

    # Любое изменение возвращает карточку в черновик — нужна повторная валидация.
    card.status = STATUS_DRAFT
    card.validation_issues = []
    card.ruleset_version = None
    card.reference_data_version = None
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.updated",
        entity_type="card",
        entity_id=card.id,
        before=before,
        after=audit_service.snapshot(card),
    )
    _commit(db, "GTIN уже привязан к другой карточке.")
    db.refresh(card)
    return _to_out(card)


def delete_card(
    db: Session, client_id: str, card_id: str, actor_id: str | None = None
) -> None:
    card = _require(db, client_id, card_id)
    before = audit_service.snapshot(card)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.deleted",
        entity_type="card",
        entity_id=card.id,
        before=before,
    )
    repo.delete(db, card)
    db.commit()


def validate_card(
    db: Session, client_id: str, card_id: str, actor_id: str | None = None
) -> CardValidateOut:
    """Прогнать одну карточку через ядро правил и обновить статус valid/error."""
    card = _require(db, client_id, card_id)
    result = _validate_one(db, client_id, card)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.validated",
        entity_type="card",
        entity_id=card.id,
        after=audit_service.snapshot(card),
        details={"is_valid": result.is_valid, "ruleset_version": RULESET_VERSION},
    )
    db.commit()
    db.refresh(card)
    return CardValidateOut(card=_to_out(card), result=result_to_schema(result))


def validate_all(
    db: Session, client_id: str, actor_id: str | None = None
) -> ValidateAllOut:
    """Массовая валидация всех карточек, ещё не отмеченных готовыми."""
    cards = repo.list_unpublished(db, client_id)
    _validate_many(db, client_id, cards)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.bulk_validated",
        entity_type="card_collection",
        entity_id=None,
        details={"count": len(cards), "ruleset_version": RULESET_VERSION},
    )
    db.commit()
    counts = _status_counts(db, client_id)
    return ValidateAllOut(
        validated=len(cards),
        valid=counts.get(STATUS_VALID, 0),
        error=counts.get(STATUS_ERROR, 0),
    )


def mark_ready(
    db: Session, client_id: str, card_id: str, actor_id: str | None = None
) -> CardOut:
    """Отметить внутреннюю готовность; внешнего обмена с НК здесь нет."""
    card = _require(db, client_id, card_id)
    if card.status != STATUS_VALID:
        raise DomainError(
            "Готовой к публикации можно отметить только валидную карточку.",
            code="NOT_VALID",
        )
    card.status = STATUS_PUBLISHED
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.marked_ready",
        entity_type="card",
        entity_id=card.id,
        after=audit_service.snapshot(card),
    )
    db.commit()
    db.refresh(card)
    return _to_out(card)


def publish_card(
    db: Session, client_id: str, card_id: str, actor_id: str | None = None
) -> CardOut:
    """Обратная совместимость старого API; действие только внутреннее."""
    return mark_ready(db, client_id, card_id, actor_id)


def build_from_variations(
    db: Session, client_id: str, data: BuildFromVariationsIn, actor_id: str | None = None
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
            data_source="variations",
            status=STATUS_DRAFT,
        )
        repo.add(db, card)
        cards.append(card)
    _validate_many(db, client_id, cards)  # автовалидация
    for card in cards:
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="card.created",
            entity_type="card",
            entity_id=card.id,
            after=audit_service.snapshot(card),
            details={"origin": "variations"},
        )
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.variations_created",
        entity_type="card_collection",
        entity_id=None,
        details={"count": len(cards), "card_ids": [card.id for card in cards]},
    )
    db.commit()
    for c in cards:
        db.refresh(c)
    return BuildFromVariationsOut(created=len(cards), cards=[_to_out(c) for c in cards])


def create_cards_bulk_items(
    db: Session,
    client_id: str,
    payloads: list[CardCreateIn],
    actor_id: str | None = None,
) -> list[Card]:
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
            packaging=data.packaging or {},
            data_source=data.data_source,
            service_comment=data.service_comment,
            status=STATUS_DRAFT,
        )
        repo.add(db, card)
        cards.append(card)
    _validate_many(db, client_id, cards)  # автовалидация сразу после импорта
    for card in cards:
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="card.created",
            entity_type="card",
            entity_id=card.id,
            after=audit_service.snapshot(card),
            details={"origin": "import"},
        )
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.bulk_created",
        entity_type="card_collection",
        entity_id=None,
        details={"count": len(cards), "card_ids": [card.id for card in cards]},
    )
    return cards


def create_cards_bulk(
    db: Session,
    client_id: str,
    payloads: list[CardCreateIn],
    actor_id: str | None = None,
) -> int:
    return len(create_cards_bulk_items(db, client_id, payloads, actor_id))


def bulk_update(
    db: Session,
    client_id: str,
    data: CardBulkUpdateIn,
    actor_id: str | None = None,
) -> CardBulkUpdateOut:
    cards = repo.list_by_ids(db, client_id, list(dict.fromkeys(data.ids)))
    if len(cards) != len(set(data.ids)):
        raise NotFoundError("Одна или несколько карточек не найдены.")
    fields = data.model_dump(exclude={"ids"}, exclude_unset=True)
    if not fields:
        raise DomainError("Не указаны поля для массового изменения.")
    invalid_nulls = sorted(
        field
        for field in {"attributes", "packaging", "data_source"}
        if field in fields and fields[field] is None
    )
    if invalid_nulls:
        raise DomainError(f"Поля нельзя очищать: {', '.join(invalid_nulls)}")
    for card in cards:
        if card.status == STATUS_PUBLISHED:
            raise ConflictError("Готовые к публикации карточки нельзя массово редактировать.")
    for card in cards:
        before = audit_service.snapshot(card)
        for key, value in fields.items():
            if key in {"attributes", "packaging"} and value is not None:
                setattr(card, key, {**(getattr(card, key) or {}), **value})
            else:
                setattr(card, key, value)
        card.status = STATUS_DRAFT
        card.validation_issues = []
        card.ruleset_version = None
        card.reference_data_version = None
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="card.bulk_updated",
            entity_type="card",
            entity_id=card.id,
            before=before,
            after=audit_service.snapshot(card),
        )
    db.commit()
    return CardBulkUpdateOut(updated=len(cards))


def export_cards(
    db: Session,
    client_id: str,
    data: CardExportIn,
    actor_id: str | None = None,
) -> bytes:
    if data.ids:
        cards = repo.list_by_ids(db, client_id, list(dict.fromkeys(data.ids)))
        if len(cards) != len(set(data.ids)):
            raise NotFoundError("Одна или несколько карточек не найдены.")
    else:
        cards, total = repo.list_cards(
            db,
            client_id,
            status=data.status,
            category_code=data.category_code,
            name=data.name,
            search=data.search,
            limit=5000,
        )
        if total > len(cards):
            raise DomainError(
                "Экспорт содержит более 5000 карточек. "
                "Уточните фильтры или выберите карточки явно.",
                code="EXPORT_LIMIT_EXCEEDED",
            )
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "id", "name", "vendor_code", "category_code", "gtin", "status",
            "data_source", "service_comment", "ruleset_version",
            "reference_data_version", "attributes", "packaging", "rd_data",
        ]
    )
    for card in cards:
        writer.writerow(
            [_csv_safe(value) for value in [
                card.id, card.name, card.vendor_code, card.category_code or "", card.gtin or "",
                card.status, card.data_source, card.service_comment or "",
                card.ruleset_version or "", card.reference_data_version or "",
                json.dumps(card.attributes, ensure_ascii=False),
                json.dumps(card.packaging, ensure_ascii=False),
                json.dumps(card.rd_data, ensure_ascii=False),
            ]]
        )
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="card.exported",
        entity_type="card_collection",
        entity_id=None,
        details={"count": len(cards), "card_ids": [card.id for card in cards]},
    )
    db.commit()
    return ("\ufeff" + output.getvalue()).encode("utf-8")


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
