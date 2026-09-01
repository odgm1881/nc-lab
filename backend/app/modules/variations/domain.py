"""Доменная логика вариаций — ЧИСТЫЙ Python. Без базы и HTTP.

Модель товара раскрывается в набор SKU декартовым произведением осей:
цвет × размер × пол × комплектность. Каждая комбинация — отдельный SKU и кандидат
в карточку (правило легпрома: цвет и размер — отдельные вариации, не смешиваются).

Тестируется за миллисекунды, позже легко заменяется ML-нормализацией.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

MAX_VARIATION_COMBINATIONS = 5_000


class VariationLimitError(ValueError):
    """Декартово произведение осей превышает безопасный предел."""


@dataclass(frozen=True)
class VariationAxes:
    """Оси вариативности модели. Пустая ось означает «неприменимо» и не размножает."""

    colors: list[str] = field(default_factory=list)
    sizes: list[str] = field(default_factory=list)
    genders: list[str] = field(default_factory=list)
    completeness: list[str] = field(default_factory=list)

    def normalized(self) -> VariationAxes:
        """Убрать пустые значения и дубликаты, сохранив порядок."""
        return VariationAxes(
            colors=_clean(self.colors),
            sizes=_clean(self.sizes),
            genders=_clean(self.genders),
            completeness=_clean(self.completeness),
        )


@dataclass(frozen=True)
class Variation:
    """Одна комбинация осей = один SKU = один кандидат в карточку."""

    color: str | None
    size: str | None
    gender: str | None
    completeness: str | None

    def as_attributes(self) -> dict[str, str]:
        """Значения осей как атрибуты карточки (только заполненные)."""
        data = {
            "color": self.color,
            "size": self.size,
            "gender": self.gender,
            "completeness": self.completeness,
        }
        return {k: v for k, v in data.items() if v is not None}


def _clean(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        v = (v or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _axis_or_none(values: list[str]) -> list[str | None]:
    return list(values) if values else [None]


def build_variations(axes: VariationAxes) -> list[Variation]:
    """Декартово произведение осей. Каждая комбинация — отдельный SKU.

    Пустая ось не размножает результат (участвует как единственное значение None).
    Порядок стабилен: цвет → размер → пол → комплектность.
    """
    ax = axes.normalized()
    count = variation_count(ax)
    if count > MAX_VARIATION_COMBINATIONS:
        raise VariationLimitError(
            "Слишком много комбинаций вариаций: "
            f"{count}. Допустимо не более {MAX_VARIATION_COMBINATIONS}."
        )
    combos = product(
        _axis_or_none(ax.colors),
        _axis_or_none(ax.sizes),
        _axis_or_none(ax.genders),
        _axis_or_none(ax.completeness),
    )
    return [Variation(color=c, size=s, gender=g, completeness=k) for c, s, g, k in combos]


def variation_count(axes: VariationAxes) -> int:
    """Сколько SKU получится, без материализации списка."""
    ax = axes.normalized()
    total = 1
    for values in (ax.colors, ax.sizes, ax.genders, ax.completeness):
        total *= len(values) if values else 1
    return total


def variation_sku(base_vendor_code: str, variation: Variation) -> str:
    """Предлагаемый артикул SKU: базовый артикул + суффиксы осей.

    Пример: TSHIRT-01 + (красный, M) -> TSHIRT-01-KRASNYJ-M.
    Это подсказка оператору, а не окончательный GTIN.
    """
    parts = [base_vendor_code.strip()]
    for value in (variation.color, variation.size, variation.gender, variation.completeness):
        if value:
            parts.append(_slug(value))
    return "-".join(p for p in parts if p)


_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _slug(value: str) -> str:
    out = []
    for ch in value.strip().lower():
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in " _/":
            out.append("-")
    return "".join(out).strip("-").upper()
