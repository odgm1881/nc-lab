# Миграции Alembic

Схема БД управляется миграциями. Прямых правок схемы нет (см. CLAUDE.md).

```bash
uv run alembic revision --autogenerate -m "описание"   # создать миграцию
uv run alembic upgrade head                            # применить
uv run alembic downgrade -1                            # откатить на шаг
```

URL берётся из `DATABASE_URL` (см. `.env`). Для SQLite включён `render_as_batch`,
чтобы работали ALTER-операции.

Для локального прототипа на SQLite таблицы также создаются автоматически при старте
приложения (`app/main.py`) и в сид-скрипте — миграции нужны прежде всего для прод-БД
на PostgreSQL.
