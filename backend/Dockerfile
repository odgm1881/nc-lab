# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Зависимости ставим через pip с кэшем BuildKit — повторные сборки не качают заново.
# Список синхронен с pyproject.toml. boto3 нужен staging/production для S3.
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip pip install \
    "fastapi[standard]>=0.115" "sqlalchemy>=2.0" alembic "pydantic-settings>=2.6" \
    "python-jose[cryptography]>=3.3" "passlib[bcrypt]>=1.7" "python-multipart>=0.0.12" \
    "openpyxl>=3.1" "psycopg[binary]>=3.2" "boto3>=1.35"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
