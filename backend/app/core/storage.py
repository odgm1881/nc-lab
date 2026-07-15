"""Обёртка над хранилищем файлов.

Если S3 настроен (есть ключи) — пишем в S3-совместимый бакет. Иначе — в локальную
папку var/storage (удобно для прототипа и тестов). Интерфейс одинаковый.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.config import settings

_LOCAL_ROOT = Path("var/storage")


class Storage:
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Сохранить объект, вернуть его ключ."""
        if settings.s3_enabled:
            return self._put_s3(key, data, content_type)
        return self._put_local(key, data)

    def get(self, key: str) -> bytes:
        if settings.s3_enabled:
            return self._get_s3(key)
        return self._get_local(key)

    # --- локальное хранилище ---
    def _put_local(self, key: str, data: bytes) -> str:
        path = _LOCAL_ROOT / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def _get_local(self, key: str) -> bytes:
        return (_LOCAL_ROOT / key).read_bytes()

    # --- S3-совместимое хранилище ---
    def _client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    def _put_s3(self, key: str, data: bytes, content_type: str) -> str:
        self._client().put_object(
            Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type
        )
        return key

    def _get_s3(self, key: str) -> bytes:
        obj = self._client().get_object(Bucket=settings.s3_bucket, Key=key)
        return obj["Body"].read()


storage = Storage()


def new_key(prefix: str, filename: str) -> str:
    """Уникальный ключ объекта на основе имени файла."""
    safe = os.path.basename(filename).replace(" ", "_")
    from uuid import uuid4

    return f"{prefix}/{uuid4().hex}_{safe}"
