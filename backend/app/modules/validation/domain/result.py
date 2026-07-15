"""Результат валидации: Issue, Severity, ValidationResult, CardView, ValidationContext.

Чистые структуры данных. Не знают ни про FastAPI, ни про SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"  # блокирует ввод в оборот
    WARNING = "warning"  # предупреждение, не блокирует
    INFO = "info"


@dataclass(frozen=True)
class Issue:
    code: str  # стабильный машиночитаемый код, напр. RD_MISSING
    severity: Severity
    message: str
    field: str | None = None  # атрибут карточки, к которому относится замечание


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        """Карточка валидна, если нет ни одной ошибки уровня ERROR."""
        return len(self.errors) == 0


@dataclass(frozen=True)
class CardView:
    """Доменное представление карточки для правил. Без ORM."""

    category_code: str | None
    gtin: str | None
    attributes: dict
    rd_data: dict
    id: str | None = None
    client_id: str | None = None


@dataclass(frozen=True)
class ValidationContext:
    """Контекст, который правилам нужен помимо самой карточки.

    gtin_index — карта «нормализованный GTIN -> id карточки» по остальным карточкам
    клиента. Нужна правилу уникальности GTIN, оставаясь чистой функцией.
    """

    gtin_index: dict[str, str] = field(default_factory=dict)
