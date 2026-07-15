"""Доменная онтология одежды: категории и их обязательные атрибуты.

Прототип онтологии — научный результат этапа 1 (см. дек, «Научная новизна»).
Категория -> набор обязательных атрибутов. Основа для объяснимых правил и
повторного использования паттернов между карточками.

Обязательные для легпрома атрибуты: вид изделия, состав сырья, размер, цвет, пол,
возрастная группа.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Человекочитаемые названия атрибутов для сообщений об ошибках.
ATTRIBUTE_LABELS = {
    "item_type": "вид изделия",
    "composition": "состав сырья",
    "size": "размер",
    "color": "цвет",
    "gender": "пол",
    "age_group": "возрастная группа",
    "brand": "бренд",
    "country": "страна производства",
}

# Базовый набор обязательных атрибутов для одежды.
_CLOTHING_REQUIRED = ["item_type", "composition", "size", "color", "gender", "age_group"]


@dataclass(frozen=True)
class CategorySpec:
    code: str
    name: str
    required_attributes: list[str] = field(default_factory=list)


# Несколько категорий легпрома по ТН ВЭД. Пополняется по мере роста словаря.
CATEGORIES: dict[str, CategorySpec] = {
    "6109": CategorySpec("6109", "Футболки, майки трикотажные", list(_CLOTHING_REQUIRED)),
    "6110": CategorySpec("6110", "Свитеры, джемперы трикотажные", list(_CLOTHING_REQUIRED)),
    "6203": CategorySpec("6203", "Костюмы, брюки мужские", list(_CLOTHING_REQUIRED)),
    "6204": CategorySpec("6204", "Костюмы, платья, брюки женские", list(_CLOTHING_REQUIRED)),
    "6205": CategorySpec("6205", "Сорочки мужские", list(_CLOTHING_REQUIRED)),
    "6206": CategorySpec("6206", "Блузки, рубашки женские", list(_CLOTHING_REQUIRED)),
    "6211": CategorySpec("6211", "Спецодежда, костюмы спортивные", list(_CLOTHING_REQUIRED)),
    "6212": CategorySpec("6212", "Бельё (бюстгальтеры, корсеты)", list(_CLOTHING_REQUIRED)),
}


def get_category(code: str | None) -> CategorySpec | None:
    if not code:
        return None
    return CATEGORIES.get(code.strip())


def required_attributes(code: str | None) -> list[str]:
    spec = get_category(code)
    return list(spec.required_attributes) if spec else list(_CLOTHING_REQUIRED)


def attribute_label(key: str) -> str:
    return ATTRIBUTE_LABELS.get(key, key)
