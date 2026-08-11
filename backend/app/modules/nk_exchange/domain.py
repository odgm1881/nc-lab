"""Независимый от HTTP/БД контракт обмена с Национальным каталогом."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

SCHEMA_VERSION = "nklab-nk-file-1"


@dataclass(frozen=True)
class ExchangeResult:
    status: str
    response: dict
    error: str | None = None


class NkAdapter(Protocol):
    def send(self, payload: Mapping[str, object], idempotency_key: str) -> ExchangeResult: ...


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


class MockAdapter:
    """Детерминированный sandbox для contract-тестов и демонстраций."""

    def send(self, payload: Mapping[str, object], idempotency_key: str) -> ExchangeResult:
        if payload.get("gtin") == "0000000000000":
            return ExchangeResult(
                status="failed",
                response={"code": "NK_TEST_REJECTED"},
                error="Тестовый адаптер отклонил карточку",
            )
        return ExchangeResult(
            status="succeeded",
            response={
                "external_id": f"mock-{payload['card_id']}",
                "idempotency_key": idempotency_key,
            },
        )


def adapter_for(mode: str) -> NkAdapter:
    if mode == "file":
        return FileAdapter()
    if mode == "mock":
        return MockAdapter()
    raise ValueError(f"Неподдерживаемый режим обмена: {mode}")
