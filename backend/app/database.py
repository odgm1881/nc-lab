"""Engine, session и зависимость get_db. Инфраструктурный слой."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: сессия на запрос, гарантированное закрытие."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
