"""Доменные исключения и их отображение в HTTP-ответы.

Домен и сервисы бросают эти исключения, не зная про HTTP. Маппинг в статусы —
в register_exception_handlers, который вызывается при сборке приложения.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Базовая доменная ошибка."""

    status_code = 400
    code = "DOMAIN_ERROR"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class AuthError(DomainError):
    status_code = 401
    code = "AUTH_ERROR"


class PayloadTooLargeError(DomainError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"


class ValidationFailedError(DomainError):
    """Карточка не прошла валидацию — бизнес-правила, не Pydantic."""

    status_code = 422
    code = "VALIDATION_FAILED"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
