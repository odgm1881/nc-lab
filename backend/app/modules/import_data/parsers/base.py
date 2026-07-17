"""Нормализация номенклатуры — ЧИСТАЯ доменная логика.

Общий интерфейс парсеров: на входе файл (bytes), на выходе список «сырых» строк
(dict заголовок→значение). Затем map_row приводит сырые заголовки к каноническим
полям номенклатуры независимо от источника (Excel, CSV, 1С).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Синонимы заголовков → каноническое поле. Ключи в нижнем регистре, без лишних пробелов.
HEADER_MAP: dict[str, str] = {
    # идентификация
    "наименование": "name",
    "название": "name",
    "модель": "name",
    "товар": "name",
    "name": "name",
    "артикул": "vendor_code",
    "код": "vendor_code",
    "sku": "vendor_code",
    "vendor_code": "vendor_code",
    "категория": "category_code",
    "тнвэд": "category_code",
    "тн вэд": "category_code",
    "код тнвэд": "category_code",
    "category": "category_code",
    "category_code": "category_code",
    "gtin": "gtin",
    "штрихкод": "gtin",
    "штрих-код": "gtin",
    "баркод": "gtin",
    "ean": "gtin",
    # вид изделия (обязательный атрибут категории)
    "вид изделия": "item_type",
    "тип изделия": "item_type",
    "вид": "item_type",
    "item_type": "item_type",
    # оси вариаций
    "цвет": "color",
    "color": "color",
    "размер": "size",
    "size": "size",
    "пол": "gender",
    "gender": "gender",
    "комплектность": "completeness",
    "комплект": "completeness",
    "completeness": "completeness",
    # атрибуты
    "состав": "composition",
    "состав сырья": "composition",
    "composition": "composition",
    "бренд": "brand",
    "торговая марка": "brand",
    "brand": "brand",
    "возрастная группа": "age_group",
    "возраст": "age_group",
    "age": "age_group",
    "age_group": "age_group",
    "страна": "country",
    "страна производства": "country",
    "country": "country",
    # РД
    "тип рд": "rd_type",
    "вид рд": "rd_type",
    "тип документа": "rd_type",
    "номер рд": "rd_number",
    "номер документа": "rd_number",
    "номер декларации": "rd_number",
    "дата рд": "rd_date",
    "дата документа": "rd_date",
    "дата декларации": "rd_date",
    "срок действия": "rd_valid_until",
    "действует до": "rd_valid_until",
    "срок рд": "rd_valid_until",
}

# Значение типа РД → канонический код.
RD_TYPE_MAP = {
    "декларация": "declaration",
    "declaration": "declaration",
    "сертификат": "certificate",
    "certificate": "certificate",
    "отказное": "refusal_letter",
    "отказное письмо": "refusal_letter",
    "refusal_letter": "refusal_letter",
}

ATTRIBUTE_FIELDS = (
    "item_type",
    "color",
    "size",
    "gender",
    "completeness",
    "composition",
    "brand",
    "age_group",
    "country",
)


@dataclass
class NomenclatureRow:
    name: str = ""
    vendor_code: str = ""
    category_code: str | None = None
    gtin: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    rd_data: dict[str, str] = field(default_factory=dict)


def _norm_header(h: str) -> str:
    return str(h or "").strip().lower()


def _norm_rd_type(value: str) -> str:
    key = str(value or "").strip().lower()
    return RD_TYPE_MAP.get(key, key)


def map_row(raw: dict) -> NomenclatureRow:
    """Привести сырую строку (заголовок→значение) к канонической номенклатуре."""
    canonical: dict[str, str] = {}
    for header, value in raw.items():
        field_name = HEADER_MAP.get(_norm_header(header))
        if not field_name:
            continue
        text = "" if value is None else str(value).strip()
        if text:
            canonical[field_name] = text

    row = NomenclatureRow(
        name=canonical.get("name", ""),
        vendor_code=canonical.get("vendor_code", ""),
        category_code=canonical.get("category_code") or None,
        gtin=canonical.get("gtin") or None,
    )
    row.attributes = {k: canonical[k] for k in ATTRIBUTE_FIELDS if k in canonical}

    rd = {}
    if "rd_type" in canonical:
        rd["type"] = _norm_rd_type(canonical["rd_type"])
    if "rd_number" in canonical:
        rd["number"] = canonical["rd_number"]
    if "rd_date" in canonical:
        rd["date"] = canonical["rd_date"]
    if "rd_valid_until" in canonical:
        rd["valid_until"] = canonical["rd_valid_until"]
    row.rd_data = rd
    return row


def map_rows(raw_rows: list[dict]) -> list[NomenclatureRow]:
    """Нормализовать список строк, пропуская полностью пустые."""
    rows = [map_row(r) for r in raw_rows]
    return [r for r in rows if r.name or r.vendor_code or r.gtin or r.attributes]
