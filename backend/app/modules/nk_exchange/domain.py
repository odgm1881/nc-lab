"""Чистый контракт обмена с Национальным каталогом.

Модуль не зависит от HTTP, FastAPI и SQLAlchemy. Здесь живут нейтральный порт,
mapping внутренней карточки в публичный контракт ``/v3/feed`` и нормализация
статусов ``/v3/feed-status``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

SCHEMA_VERSION = "nklab-nk-file-2"


@dataclass(frozen=True)
class ExchangeResult:
    status: str
    response: dict
    error: str | None = None
    error_code: str | None = None
    external_id: str | None = None
    retryable: bool = False
    retry_after_seconds: int | None = None


class NkAdapter(Protocol):
    def send(self, payload: Mapping[str, object], idempotency_key: str) -> ExchangeResult: ...

    def refresh(self, external_id: str) -> ExchangeResult: ...


def build_nk_feed(
    payload: Mapping[str, object],
    attribute_map: Mapping[str, str],
    category_map: Mapping[str, int],
) -> dict:
    """Преобразовать нейтральную карточку в JSON метода ``POST /v3/feed``.

    Идентификаторы атрибутов и категорий отличаются между товарными группами,
    поэтому они приходят из проверенной конфигурации, а не зашиваются в код.
    Неизвестные атрибуты намеренно не отправляются.
    """
    name = str(payload.get("name") or "").strip()
    gtin = str(payload.get("gtin") or "").strip()
    tnved = str(payload.get("category_code") or "").strip()
    if not name or not gtin or not tnved:
        raise ValueError("Для НК обязательны name, gtin и category_code (ТН ВЭД).")

    attributes = payload.get("attributes")
    if not isinstance(attributes, Mapping):
        attributes = {}

    entry: dict[str, object] = {
        "gtin": gtin,
        "tnved": tnved,
        "good_name": name,
        "identified_by": [
            {
                "value": gtin,
                "type": "gtin",
                "multiplier": 1,
                "level": "trade-unit",
                "unit": "шт",
            }
        ],
    }
    brand = str(attributes.get("brand") or "").strip()
    if not brand:
        raise ValueError("Для новой карточки НК обязателен атрибут brand.")
    entry["brand"] = brand

    category_id = category_map.get(tnved)
    if category_id is None:
        raise ValueError(f"Для ТН ВЭД {tnved} не настроен подтверждённый cat_id НК.")
    entry["categories"] = [category_id]

    good_attrs: list[dict[str, str]] = []
    for field_name, attr_id in attribute_map.items():
        value = _source_value(payload, attributes, field_name)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            text = str(item).strip()
            if text:
                good_attrs.append({"attr_id": str(attr_id), "attr_value": text})
    if good_attrs:
        entry["good_attrs"] = good_attrs
    else:
        raise ValueError("Нет ни одного заполненного атрибута с подтверждённым attr_id НК.")
    validate_nk_feed_contract(entry)
    return entry


def validate_nk_feed_contract(feed: Mapping[str, object]) -> None:
    """Защитить HTTP-границу от отправки структурно некорректного фида."""
    required_text = ("gtin", "tnved", "good_name", "brand")
    if any(not isinstance(feed.get(key), str) or not feed.get(key) for key in required_text):
        raise ValueError("Контракт НК: обязательные текстовые поля заполнены некорректно.")
    categories = feed.get("categories")
    if not isinstance(categories, list) or not categories or not all(
        isinstance(value, int) for value in categories
    ):
        raise ValueError("Контракт НК: categories должен содержать числовой cat_id.")
    identifiers = feed.get("identified_by")
    if not isinstance(identifiers, list) or len(identifiers) != 1:
        raise ValueError("Контракт НК: требуется один идентификатор торговой единицы.")
    attrs = feed.get("good_attrs")
    if not isinstance(attrs, list) or not attrs:
        raise ValueError("Контракт НК: good_attrs не может быть пустым.")
    for item in attrs:
        if not isinstance(item, Mapping) or not isinstance(item.get("attr_id"), str):
            raise ValueError("Контракт НК: атрибут должен содержать строковый attr_id.")


def _source_value(
    payload: Mapping[str, object], attributes: Mapping[str, object], field_name: str
):
    if field_name == "rd_number_date":
        rd_data = payload.get("rd_data")
        if isinstance(rd_data, Mapping):
            number = str(rd_data.get("number") or "").strip()
            date = str(rd_data.get("date") or "").strip()
            return f"{number}:::{date}" if number and date else None
        return None
    if field_name.startswith("rd_data.") or field_name.startswith("packaging."):
        section_name, key = field_name.split(".", 1)
        section = payload.get(section_name)
        return section.get(key) if isinstance(section, Mapping) else None
    return attributes.get(field_name)


def normalize_feed_status(body: Mapping[str, object]) -> ExchangeResult:
    """Привести ответ ``/v3/feed-status`` к внутренним статусам."""
    raw_result = body.get("result")
    result = raw_result if isinstance(raw_result, Mapping) else body
    external_status = str(result.get("status") or "").strip()
    feed_id = result.get("feed_id")
    external_id = str(feed_id) if feed_id is not None else None

    if external_status in {"Received", "Processing"}:
        status = "processing"
    elif external_status in {"Moderated", "Signed"}:
        status = "succeeded"
    elif external_status == "Rejected":
        status = "failed"
    else:
        return ExchangeResult(
            status="failed",
            response=dict(body),
            error="НК вернул неизвестный статус обработки фида.",
            error_code="NK_UNKNOWN_STATUS",
            external_id=external_id,
        )

    errors = extract_feed_errors(result)
    if errors:
        status = "failed"
    return ExchangeResult(
        status=status,
        response=dict(body),
        error="; ".join(item["message"] for item in errors) or None,
        error_code=errors[0]["code"] if errors else None,
        external_id=external_id,
    )


def extract_feed_errors(result: Mapping[str, object]) -> list[dict[str, str]]:
    """Извлечь понятные ошибки из краткого и verbose-ответа НК."""
    errors: list[dict[str, str]] = []
    items = result.get("item")
    if isinstance(items, Mapping):
        items = [items]
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            message = item.get("message") or item.get("status_message")
            if message:
                errors.append(
                    {
                        "code": str(item.get("status_code") or "NK_VALIDATION_ERROR"),
                        "message": str(message),
                        "field": str(item.get("attribute_id") or ""),
                    }
                )

    details = result.get("error_details")
    if isinstance(details, Mapping):
        common = details.get("commonError")
        if isinstance(common, Mapping) and common.get("text"):
            errors.append(
                {"code": str(common.get("code") or "NK_ERROR"), "message": str(common["text"])}
            )
    return errors


class FileAdapter:
    """Готовит пакет без ложного заявления о передаче во внешний сервис."""

    def send(self, payload: Mapping[str, object], idempotency_key: str) -> ExchangeResult:
        return ExchangeResult(
            status="prepared",
            response={
                "message": "Пакет подготовлен для файловой передачи в НК",
                "schema_version": SCHEMA_VERSION,
                "idempotency_key": idempotency_key,
            },
        )

    def refresh(self, external_id: str) -> ExchangeResult:
        raise ValueError("Файловый обмен не имеет внешнего статуса.")


class MockAdapter:
    """Детерминированный sandbox для contract-тестов и демонстраций."""

    def send(self, payload: Mapping[str, object], idempotency_key: str) -> ExchangeResult:
        if payload.get("gtin") == "0000000000000":
            return ExchangeResult(
                status="failed",
                response={"code": "NK_TEST_REJECTED"},
                error="Тестовый адаптер отклонил карточку",
                error_code="NK_TEST_REJECTED",
            )
        return ExchangeResult(
            status="succeeded",
            response={
                "external_id": f"mock-{payload['card_id']}",
                "idempotency_key": idempotency_key,
            },
            external_id=f"mock-{payload['card_id']}",
        )

    def refresh(self, external_id: str) -> ExchangeResult:
        return ExchangeResult(
            status="succeeded",
            response={"external_id": external_id, "status": "Signed"},
            external_id=external_id,
        )
