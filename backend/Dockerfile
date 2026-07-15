FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Зависимости ставим напрямую через pip (без внешних реестров, кроме PyPI).
# Список синхронен с pyproject.toml. Локальная разработка использует uv (см. README).
COPY pyproject.toml ./
RUN pip install \
    "fastapi[standard]>=0.115" "sqlalchemy>=2.0" alembic "pydantic-settings>=2.6" \
    "python-jose[cryptography]>=3.3" "passlib[bcrypt]>=1.7" "python-multipart>=0.0.12" \
    "openpyxl>=3.1" "boto3>=1.35" "psycopg[binary]>=3.2"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
