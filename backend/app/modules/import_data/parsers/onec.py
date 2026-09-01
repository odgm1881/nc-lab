"""Парсер воспроизводимых выгрузок 1С.

Поддерживаются CSV с разделителем ``;`` (UTF-8/Windows-1251) и базовый CommerceML
2.x. Специфичные свойства конкретной конфигурации 1С по-прежнему настраиваются
сохраняемым профилем сопоставления колонок.
"""

from __future__ import annotations

from xml.etree import ElementTree

from app.modules.import_data.parsers.base import SOURCE_ROW_NUMBER
from app.modules.import_data.parsers.csv_parser import parse_csv


def parse_onec(content: bytes) -> list[dict]:
    if content.lstrip().startswith(b"<"):
        return _parse_commerceml(content)
    return parse_csv(content, delimiter=";")


def _parse_commerceml(content: bytes) -> list[dict]:
    upper = content.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("DTD и XML entities в выгрузке 1С не поддерживаются")
    root = ElementTree.fromstring(content)
    rows: list[dict] = []
    for row_number, product in enumerate(_elements(root, "Товар"), start=1):
        raw: dict[str, str | int] = {
            "Наименование": _child_text(product, "Наименование"),
            "Артикул": _child_text(product, "Артикул") or _child_text(product, "Ид"),
            "Штрихкод": _first_descendant_text(product, "Штрихкод"),
            SOURCE_ROW_NUMBER: row_number,
        }
        base_unit = next(_elements(product, "БазоваяЕдиница"), None)
        if base_unit is not None and not raw["Штрихкод"]:
            raw["Штрихкод"] = base_unit.attrib.get("Штрихкод", "")

        # Стандартные реквизиты 1С уже имеют понятные имена и проходят через
        # общий словарь HEADER_MAP (бренд, страна, состав, ТН ВЭД и т.д.).
        for prop in _elements(product, "ЗначениеРеквизита"):
            name = _child_text(prop, "Наименование")
            value = _child_text(prop, "Значение")
            if name and value:
                raw[name] = value
        for prop in _elements(product, "ХарактеристикаТовара"):
            name = _child_text(prop, "Наименование")
            value = _child_text(prop, "Значение")
            if name and value:
                raw[name] = value

        if any(str(value).strip() for key, value in raw.items() if key != SOURCE_ROW_NUMBER):
            rows.append(raw)
    return rows


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _elements(root: ElementTree.Element, name: str):
    return (element for element in root.iter() if _local_name(element.tag) == name)


def _child_text(root: ElementTree.Element, name: str) -> str:
    for child in root:
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _first_descendant_text(root: ElementTree.Element, name: str) -> str:
    element = next(_elements(root, name), None)
    return (element.text or "").strip() if element is not None else ""
