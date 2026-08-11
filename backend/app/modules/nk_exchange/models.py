from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import JSONBType
from app.database import Base


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class NkExchange(Base):
    """Неизменяемый запрос и обновляемый результат одной операции обмена."""

    __tablename__ = "nk_exchanges"
    __table_args__ = (
        UniqueConstraint("client_id", "idempotency_key", name="uq_nk_exchange_client_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="file")
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    request_payload: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
