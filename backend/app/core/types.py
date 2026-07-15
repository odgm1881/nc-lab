"""Переносимые типы колонок.

JSONB на PostgreSQL, обычный JSON на SQLite (для локального прототипа).
Стратегия хранения атрибутов — см. ARCHITECTURE.md и навык nk-domain.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# На postgresql рендерится в JSONB, на остальных диалектах — в JSON.
JSONBType = JSON().with_variant(JSONB(), "postgresql")
