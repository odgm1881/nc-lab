"""Инфраструктурные адаптеры Национального каталога."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import Settings
from app.modules.nk_exchange.domain import (
    ExchangeResult,
    FileAdapter,
    MockAdapter,
    NkAdapter,
    build_nk_feed,
    normalize_feed_status,
)


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str]


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> TransportResponse:
        request = Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                return TransportResponse(response.status, response.read(), dict(response.headers))
        except HTTPError as exc:
            return TransportResponse(exc.code, exc.read(), dict(exc.headers or {}))
        except (URLError, TimeoutError) as exc:
            raise ConnectionError("НК недоступен или превысил таймаут запроса.") from exc


class NkApiAdapter:
    """Адаптер публичных методов API НК ``feed`` и ``feed-status``."""

    def __init__(self, settings: Settings, transport: UrllibTransport | None = None):
        self.settings = settings
        self.transport = transport or UrllibTransport()

    def send(self, payload: Mapping[str, object], idempotency_key: str) -> ExchangeResult:
        del idempotency_key  # идемпотентность обеспечивается журналом НК-ЛАБ до HTTP-вызова
        try:
            feed = build_nk_feed(
                payload, self.settings.nk_attribute_map, self.settings.nk_category_map
            )
        except ValueError as exc:
            return ExchangeResult(
                status="failed",
                response={},
                error=str(exc),
                error_code="NK_MAPPING_ERROR",
            )
        response = self._request("POST", "/v3/feed", body=feed)
        if isinstance(response, ExchangeResult):
            return response
        body = _sanitized_json_body(response.body)
        result = body.get("result") if isinstance(body.get("result"), Mapping) else body
        feed_id = result.get("feed_id") if isinstance(result, Mapping) else None
        if feed_id is None:
            return ExchangeResult(
                status="failed",
                response=body,
                error=_error_message(body, "НК не вернул идентификатор фида."),
                error_code="NK_INVALID_RESPONSE",
            )
        return ExchangeResult(
            status="processing",
            response=body,
            external_id=str(feed_id),
        )

    def refresh(self, external_id: str) -> ExchangeResult:
        response = self._request(
            "GET", "/v3/feed-status", extra_query={"feed_id": external_id, "verbose": "true"}
        )
        if isinstance(response, ExchangeResult):
            return response
        return normalize_feed_status(_sanitized_json_body(response.body))

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        extra_query: Mapping[str, str] | None = None,
    ) -> TransportResponse | ExchangeResult:
        query = {"format": "json"}
        if self.settings.nk_api_key:
            query["apikey"] = self.settings.nk_api_key
        if self.settings.nk_supplier_key:
            query["supplier_key"] = self.settings.nk_supplier_key
        query.update(extra_query or {})
        headers = {"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"}
        if self.settings.nk_bearer_token:
            headers["Authorization"] = f"Bearer {self.settings.nk_bearer_token}"
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        try:
            response = self.transport.request(
                method,
                f"{self.settings.nk_api_base_url.rstrip('/')}{path}?{urlencode(query)}",
                headers,
                encoded,
                self.settings.nk_api_timeout_seconds,
            )
        except ConnectionError as exc:
            return ExchangeResult(
                status="failed",
                response={},
                error=str(exc),
                error_code="NK_CONNECTION_ERROR",
                retryable=True,
            )
        if 200 <= response.status_code < 300:
            return response
        parsed = _sanitized_json_body(response.body)
        retryable = response.status_code in {408, 429, 500, 502, 503, 504}
        return ExchangeResult(
            status="failed",
            response={"http_status": response.status_code, "body": parsed},
            error=_error_message(parsed, f"НК вернул HTTP {response.status_code}."),
            error_code=f"NK_HTTP_{response.status_code}",
            retryable=retryable,
            retry_after_seconds=_retry_after_seconds(response.headers),
        )


def adapter_for(mode: str, settings: Settings) -> NkAdapter:
    if mode == "file":
        return FileAdapter()
    if mode == "mock":
        return MockAdapter()
    if mode == "api":
        if not settings.nk_api_enabled:
            raise ValueError("API-обмен с НК отключён. Установите NK_API_ENABLED=true.")
        return NkApiAdapter(settings)
    raise ValueError(f"Неподдерживаемый режим обмена: {mode}")


def _sanitized_json_body(body: bytes) -> dict:
    if not body:
        return {}
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw": body.decode("utf-8", errors="replace")[:4000]}
    parsed = value if isinstance(value, dict) else {"result": value}
    return _sanitize(parsed)


def _sanitize(value):
    if isinstance(value, dict):
        return {
            str(key): (
                "***"
                if str(key).lower() in {"apikey", "token", "authorization"}
                else _sanitize(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _error_message(body: Mapping[str, object], fallback: str) -> str:
    error = body.get("error") or body.get("message")
    if isinstance(error, Mapping):
        error = error.get("message") or error.get("text") or error.get("description")
    return str(error)[:2000] if error else fallback


def _retry_after_seconds(headers: Mapping[str, str]) -> int | None:
    raw = next(
        (value for key, value in headers.items() if key.lower() == "retry-after"),
        None,
    )
    if raw is None:
        return None
    try:
        return max(1, min(3600, int(raw)))
    except ValueError:
        return None
