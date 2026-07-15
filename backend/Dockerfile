FROM python:3.13-slim

# uv для установки зависимостей
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml ./
RUN uv pip install --system --no-cache \
    "fastapi[standard]>=0.115" "sqlalchemy>=2.0" alembic "pydantic-settings>=2.6" \
    "python-jose[cryptography]>=3.3" "passlib[bcrypt]>=1.7" "python-multipart>=0.0.12" \
    "openpyxl>=3.1" "boto3>=1.35" "psycopg[binary]>=3.2"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
