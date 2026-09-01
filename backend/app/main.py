"""Сборка приложения FastAPI: роутеры модулей, обработчики ошибок, CORS.

Модульный монолит: каждый модуль-фича подключает свой роутер здесь.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.observability import configure_logging, register_request_logging, request_metrics
from app.core.storage import storage
from app.database import SessionLocal


def _create_tables_for_sqlite() -> None:
    """Локальный прототип на SQLite: создаём таблицы из моделей.

    В проде (PostgreSQL) схема управляется миграциями Alembic — здесь ничего не
    создаётся. Это удобство только для мгновенного запуска прототипа.
    """
    if not settings.is_sqlite:
        return
    # Импортируем модели, чтобы они зарегистрировались в метаданных Base.
    from app.database import Base, engine
    from app.modules.audit import models as _audit  # noqa: F401
    from app.modules.auth import models as _auth  # noqa: F401
    from app.modules.catalog import models as _catalog  # noqa: F401
    from app.modules.import_data import models as _import  # noqa: F401
    from app.modules.nk_exchange import models as _nk_exchange  # noqa: F401
    from app.modules.operator import models as _operator  # noqa: F401
    from app.modules.pilots import models as _pilots  # noqa: F401
    from app.modules.validation_rulesets import models as _validation_rulesets  # noqa: F401

    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _create_tables_for_sqlite()
    yield


configure_logging()

app = FastAPI(
    title="НК-ЛАБ API",
    version=settings.app_version,
    description=(
        "Платформа подготовки и валидации карточек товаров для Национального каталога "
        "и маркировки. Валидация карточек, вариаций, GTIN и РД до заказа кодов."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
register_request_logging(app)


@app.get("/api/health/live", tags=["health"])
def liveness() -> dict:
    return {"status": "ok", "env": settings.app_env, "version": settings.app_version}


@app.get("/api/health/ready", tags=["health"])
def readiness() -> dict:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        if not storage.ready():
            raise RuntimeError("storage unavailable")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {
        "status": "ready",
        "version": settings.app_version,
        "components": {"database": "ready", "storage": "ready"},
    }


@app.get("/api/health", tags=["health"], include_in_schema=False)
def health_compatibility() -> dict:
    """Совместимость со старым health endpoint."""
    return liveness()


@app.get("/api/metrics", include_in_schema=False, response_class=PlainTextResponse)
def metrics(authorization: str | None = Header(default=None)) -> str:
    if settings.metrics_token and authorization != f"Bearer {settings.metrics_token}":
        raise HTTPException(status_code=401, detail="invalid metrics token")
    return request_metrics.render()


# --- подключение роутеров модулей ---
from app.modules.auth.router import router as auth_router  # noqa: E402
from app.modules.catalog.router import router as catalog_router  # noqa: E402
from app.modules.gtin.router import router as gtin_router  # noqa: E402
from app.modules.import_data.router import router as import_router  # noqa: E402
from app.modules.nk_exchange.router import router as nk_exchange_router  # noqa: E402
from app.modules.operator.router import router as operator_router  # noqa: E402
from app.modules.pilot_metrics.router import router as pilot_metrics_router  # noqa: E402
from app.modules.pilots.router import router as pilots_router  # noqa: E402
from app.modules.rd.router import router as rd_router  # noqa: E402
from app.modules.validation.router import router as validation_router  # noqa: E402
from app.modules.validation_rulesets.router import (  # noqa: E402
    router as validation_rulesets_router,
)
from app.modules.variations.router import router as variations_router  # noqa: E402

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(import_router, prefix="/api/import", tags=["import"])
app.include_router(nk_exchange_router, prefix="/api/integration/nk", tags=["nk integration"])
app.include_router(catalog_router, prefix="/api/cards", tags=["catalog"])
app.include_router(variations_router, prefix="/api/variations", tags=["variations"])
app.include_router(validation_router, prefix="/api/validation", tags=["validation"])
app.include_router(
    validation_rulesets_router,
    prefix="/api/validation/rulesets",
    tags=["validation rule sets"],
)
app.include_router(gtin_router, prefix="/api/gtin", tags=["gtin"])
app.include_router(rd_router, prefix="/api/rd", tags=["rd"])
app.include_router(operator_router, prefix="/api/operator", tags=["operator"])
app.include_router(pilot_metrics_router, prefix="/api/pilot", tags=["pilot"])
app.include_router(pilots_router, prefix="/api/pilots", tags=["pilots"])
