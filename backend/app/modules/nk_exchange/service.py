from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.core.observability import get_correlation_id
from app.modules.audit import service as audit_service
from app.modules.catalog import service as catalog_service
from app.modules.catalog.models import Card
from app.modules.nk_exchange.adapters import adapter_for
from app.modules.nk_exchange.domain import SCHEMA_VERSION
from app.modules.nk_exchange.models import NkExchange
from app.modules.nk_exchange.schemas import (
    ExchangeBulkOut,
    ExchangeCreateIn,
    ExchangeListOut,
    ExchangeOut,
    ExchangeQueueSummaryOut,
    IntegrationStatusOut,
)


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


def _fingerprint(payload: dict, mode: str) -> str:
    canonical = json.dumps(
        {"mode": mode, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _execute(item: NkExchange) -> None:
    try:
        adapter = adapter_for(item.mode, settings)
    except ValueError as exc:
        raise DomainError(str(exc), code="NK_NOT_CONFIGURED") from exc
    started = time.perf_counter()
    max_attempts = settings.nk_api_max_attempts if item.mode == "api" else 1
    result = None
    for _ in range(max_attempts):
        item.attempts += 1
        item.last_attempt_at = datetime.now(UTC)
        try:
            result = adapter.send(item.request_payload, item.idempotency_key)
        except Exception as exc:  # внешняя граница не должна оставлять pending навсегда
            result = None
            item.status = "failed"
            item.response_payload = {}
            item.error = f"Непредвиденная ошибка адаптера: {type(exc).__name__}."
            item.error_code = "NK_ADAPTER_ERROR"
            item.retryable = True
            break
        if not result.retryable:
            break
        if result.retry_after_seconds:
            break
    item.duration_ms = round((time.perf_counter() - started) * 1000)
    if result is None:
        item.next_retry_at = datetime.now(UTC) + timedelta(minutes=5)
        return
    item.status = result.status
    item.response_payload = result.response
    item.error = result.error
    item.error_code = result.error_code
    item.external_id = result.external_id
    item.retryable = result.retryable and result.status == "failed"
    if item.retryable:
        delay = result.retry_after_seconds or min(3600, 60 * (2 ** min(item.attempts, 6)))
        item.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
    else:
        item.next_retry_at = None


def create(
    db: Session, client_id: str, data: ExchangeCreateIn, actor_id: str | None
) -> ExchangeOut:
    card = catalog_service.require_current_published_card(
        db,
        client_id,
        data.card_id,
        actor_id,
    )
    payload = _payload(card)
    fingerprint = _fingerprint(payload, data.mode)
    key = data.idempotency_key or f"auto-{data.mode}-{fingerprint[:48]}"
    existing = db.scalar(
        select(NkExchange).where(
            NkExchange.client_id == client_id, NkExchange.idempotency_key == key
        )
    )
    if existing:
        if (
            existing.card_id != card.id
            or existing.mode != data.mode
            or existing.request_fingerprint != fingerprint
        ):
            raise ConflictError("Ключ идемпотентности уже использован для другого запроса.")
        return ExchangeOut.model_validate(existing)

    item = NkExchange(
        client_id=client_id,
        card_id=card.id,
        idempotency_key=key,
        request_fingerprint=fingerprint,
        mode=data.mode,
        status="pending",
        request_payload=payload,
        response_payload={},
        attempts=0,
        correlation_id=(get_correlation_id() or "")[:64] or None,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Операция с таким ключом уже существует.") from exc
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


def list_items(
    db: Session,
    client_id: str,
    limit: int,
    offset: int,
    status: str | None = None,
    reconciliation_status: str | None = None,
) -> ExchangeListOut:
    filters = [NkExchange.client_id == client_id]
    if status:
        filters.append(NkExchange.status == status)
    if reconciliation_status:
        filters.append(NkExchange.reconciliation_status == reconciliation_status)
    total = (
        db.scalar(select(func.count()).select_from(NkExchange).where(*filters))
        or 0
    )
    stmt = (
        select(NkExchange)
        .where(*filters)
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


def retry_due(
    db: Session,
    client_id: str,
    actor_id: str | None,
    limit: int = 100,
) -> ExchangeBulkOut:
    now = datetime.now(UTC)
    items = list(
        db.scalars(
            select(NkExchange)
            .where(
                NkExchange.client_id == client_id,
                NkExchange.status == "failed",
                NkExchange.retryable.is_(True),
                NkExchange.next_retry_at <= now,
            )
            .order_by(NkExchange.next_retry_at.asc())
            .limit(limit)
        )
    )
    for item in items:
        _execute(item)
        audit_service.record(
            db,
            client_id=client_id,
            actor_id=actor_id,
            action="nk_exchange.auto_retried",
            entity_type="nk_exchange",
            entity_id=item.id,
            details={"attempts": item.attempts, "status": item.status},
        )
    db.commit()
    return ExchangeBulkOut(
        processed=len(items),
        succeeded=sum(item.status != "failed" for item in items),
        failed=sum(item.status == "failed" for item in items),
        items=[ExchangeOut.model_validate(item) for item in items],
    )


def reconcile(
    db: Session,
    client_id: str,
    exchange_id: str,
    actor_id: str | None,
) -> ExchangeOut:
    item = _require_exchange(db, client_id, exchange_id)
    card = db.get(Card, item.card_id)
    if card is None or card.client_id != client_id:
        item.reconciliation_status = "card_missing"
    else:
        current = _fingerprint(_payload(card), item.mode)
        if current != item.request_fingerprint:
            item.reconciliation_status = "stale_payload"
        elif item.status == "processing":
            item.reconciliation_status = "remote_pending"
        elif item.status == "failed":
            item.reconciliation_status = "remote_failed"
        else:
            item.reconciliation_status = "in_sync"
    item.last_reconciled_at = datetime.now(UTC)
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="nk_exchange.reconciled",
        entity_type="nk_exchange",
        entity_id=item.id,
        details={"reconciliation_status": item.reconciliation_status},
    )
    db.commit()
    db.refresh(item)
    return ExchangeOut.model_validate(item)


def queue_summary(db: Session, client_id: str) -> ExchangeQueueSummaryOut:
    items = list(db.scalars(select(NkExchange).where(NkExchange.client_id == client_id)))
    now = datetime.now(UTC)
    return ExchangeQueueSummaryOut(
        total=len(items),
        failed=sum(item.status == "failed" for item in items),
        retry_due=sum(
            item.status == "failed"
            and item.retryable
            and bool(item.next_retry_at and item.next_retry_at <= now)
            for item in items
        ),
        processing=sum(item.status == "processing" for item in items),
        stale_payload=sum(item.reconciliation_status == "stale_payload" for item in items),
    )


def refresh(db: Session, client_id: str, exchange_id: str, actor_id: str | None) -> ExchangeOut:
    item = _require_exchange(db, client_id, exchange_id)
    if item.mode != "api" or not item.external_id:
        raise ConflictError("Обновление статуса доступно только для отправленного API-фида.")
    if item.status not in {"processing", "failed"}:
        raise ConflictError("Операция уже завершена и не требует обновления статуса.")
    try:
        adapter = adapter_for("api", settings)
    except ValueError as exc:
        raise DomainError(str(exc), code="NK_NOT_CONFIGURED") from exc
    started = time.perf_counter()
    item.attempts += 1
    item.last_attempt_at = datetime.now(UTC)
    result = adapter.refresh(item.external_id)
    item.duration_ms = round((time.perf_counter() - started) * 1000)
    item.status = result.status
    item.response_payload = result.response
    item.error = result.error
    item.error_code = result.error_code
    item.external_id = result.external_id or item.external_id
    item.retryable = result.retryable and result.status == "failed"
    item.next_retry_at = (
        datetime.now(UTC) + timedelta(seconds=result.retry_after_seconds or 300)
        if item.retryable
        else None
    )
    audit_service.record(
        db,
        client_id=client_id,
        actor_id=actor_id,
        action="nk_exchange.refreshed",
        entity_type="nk_exchange",
        entity_id=item.id,
        details={"attempts": item.attempts, "status": item.status},
    )
    db.commit()
    db.refresh(item)
    return ExchangeOut.model_validate(item)


def integration_status() -> IntegrationStatusOut:
    if settings.nk_bearer_token:
        auth_method = "bearer"
    elif settings.nk_api_key:
        auth_method = "api_key"
    else:
        auth_method = "none"
    return IntegrationStatusOut(
        api_enabled=settings.nk_api_enabled,
        base_url=settings.nk_api_base_url,
        auth_method=auth_method,
        attribute_mappings=len(settings.nk_attribute_map),
        category_mappings=len(settings.nk_category_map),
    )


def export_payload(db: Session, client_id: str, exchange_id: str) -> bytes:
    item = _require_exchange(db, client_id, exchange_id)
    return (json.dumps(item.request_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
