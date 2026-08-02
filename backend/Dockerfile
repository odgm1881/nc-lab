# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Production использует ровно те версии и hashes, которые зафиксированы uv.lock
# и проверены CI. requirements.lock генерируется командой из первой строки файла.
COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --require-hashes --no-deps -r requirements.lock

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
