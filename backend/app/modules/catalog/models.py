"""SQLAlchemy-модель карточки товара НК.

Стратегия JSONB: фиксированные поля — колонками (поиск, джойны, уникальность),
изменчивые атрибуты категории и сведения РД — в JSONB.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import JSONBType
from app.database import Base

# published — историческое имя внутреннего статуса «готова к публикации», не внешний обмен.
STATUS_DRAFT = "draft"
STATUS_VALIDATING = "validating"
STATUS_VALID = "valid"
STATUS_ERROR = "error"
STATUS_PUBLISHED = "published"

ALL_STATUSES = (STATUS_DRAFT, STATUS_VALIDATING, STATUS_VALID, STATUS_ERROR, STATUS_PUBLISHED)


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class Card(Base):
    __tablename__ = "cards"
    # GTIN уникален в рамках клиента (1 GTIN = 1 карточка). NULL допускается для черновиков.
    __table_args__ = (UniqueConstraint("client_id", "gtin", name="uq_card_client_gtin"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    vendor_code: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    category_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    gtin: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_DRAFT, index=True
    )

    # Гибкие атрибуты категории и сведения РД — в JSONB.
    attributes: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    rd_data: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    # Результат последней валидации (список замечаний) — для отображения в кабинете.
    validation_issues: Mapped[list] = mapped_column(JSONBType, nullable=False, default=list)
    packaging: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    data_source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    service_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ruleset_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference_data_version: Mapped[str | None] = mapped_column(String(40), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
