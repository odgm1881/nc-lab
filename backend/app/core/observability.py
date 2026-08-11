"""Минимальная наблюдаемость для модульного монолита: JSON-логи и correlation ID."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from contextvars import ContextVar
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, int], int] = defaultdict(int)
        self._duration_sum: dict[str, float] = defaultdict(float)

    def observe(self, method: str, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self._requests[(method, status_code)] += 1
            self._duration_sum[method] += duration_seconds

    def render(self) -> str:
        lines = [
            "# HELP nklab_http_requests_total Total HTTP requests.",
            "# TYPE nklab_http_requests_total counter",
        ]
        with self._lock:
            for (method, status), count in sorted(self._requests.items()):
                lines.append(
                    f'nklab_http_requests_total{{method="{method}",status="{status}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP nklab_http_request_duration_seconds_sum Total request duration.",
                    "# TYPE nklab_http_request_duration_seconds_sum counter",
                ]
            )
            for method, duration in sorted(self._duration_sum.items()):
                lines.append(
                    f'nklab_http_request_duration_seconds_sum{{method="{method}"}} {duration:.6f}'
                )
        return "\n".join(lines) + "\n"


class FixedWindowRateLimiter:
    """Локальный предохранитель; общий лимит дополнительно задаётся на reverse proxy."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        current = now if now is not None else time.monotonic()
        cutoff = current - 60
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(current)
            return True


request_metrics = RequestMetrics()
auth_rate_limiter = FixedWindowRateLimiter()


def get_correlation_id() -> str | None:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("correlation_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())


def register_request_logging(app: FastAPI) -> None:
    logger = logging.getLogger("nklab.http")

    @app.middleware("http")
    async def request_log_middleware(request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
        token = _correlation_id.set(correlation_id)
        started = time.perf_counter()
        status_code = 500
        try:
            if (
                settings.app_env in {"staging", "production"}
                and request.url.path in {"/api/auth/login", "/api/auth/register"}
            ):
                host = request.client.host if request.client else "unknown"
                key = f"{host}:{request.url.path}"
                if not auth_rate_limiter.allow(key, settings.auth_rate_limit_per_minute):
                    status_code = 429
                    response = JSONResponse(
                        status_code=429,
                        content={
                            "error": {
                                "code": "RATE_LIMITED",
                                "message": "Слишком много попыток. Повторите через минуту.",
                            }
                        },
                        headers={"Retry-After": "60"},
                    )
                else:
                    response = await call_next(request)
                    status_code = response.status_code
            else:
                response = await call_next(request)
                status_code = response.status_code
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        finally:
            request_metrics.observe(
                request.method, status_code, time.perf_counter() - started
            )
            _correlation_id.reset(token)
        response.headers["x-correlation-id"] = correlation_id
        logger.info(
            "request_completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response
