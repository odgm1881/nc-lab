from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.core.observability import get_correlation_id
from app.modules.audit.models import AuditEvent


def snapshot(entity: Any) -> dict:
    """JSON-совместимый снимок колонок SQLAlchemy-сущности."""
    result: dict = {}
    for attr in inspect(entity).mapper.column_attrs:
        value = getattr(entity, attr.key)
        result[attr.key] = value.isoformat() if hasattr(value, "isoformat") else value
    return result


def record(
    db: Session,
    *,
    client_id: str | None,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    before: dict | None = None,
    after: dict | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        client_id=client_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        details=details or {},
        correlation_id=get_correlation_id(),
    )
    db.add(event)
    return event


def history(db: Session, client_id: str, entity_type: str, entity_id: str) -> list[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.client_id == client_id,
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id,
        )
        .order_by(AuditEvent.created_at.desc())
    )
    return list(db.scalars(stmt))
