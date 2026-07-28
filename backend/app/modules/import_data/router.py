"""API-слой импорта. Только HTTP. Загрузка файла multipart/form-data."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AuthError, PayloadTooLargeError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.import_data import service
from app.modules.import_data.schemas import (
    ImportCommitOut,
    ImportJobOut,
    ImportPreviewOut,
)

router = APIRouter()


def _client_id(user: User) -> str:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return user.client_id


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes / (1024 * 1024)
        raise PayloadTooLargeError(f"Размер файла превышает допустимый лимит {max_mb:g} МБ.")
    return content


@router.post("/preview", response_model=ImportPreviewOut)
async def preview(
    file: UploadFile = File(...),
    source: str | None = Form(None),
    user: User = Depends(get_current_user),
) -> ImportPreviewOut:
    """Распарсить и показать нормализованную номенклатуру без сохранения."""
    content = await _read_upload(file)
    return service.preview(file.filename or "upload", source, content)


@router.post("/commit", response_model=ImportCommitOut, status_code=201)
async def commit(
    file: UploadFile = File(...),
    source: str | None = Form(None),
    create_cards: bool = Form(True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportCommitOut:
    """Сохранить файл, создать задание импорта и карточки-черновики."""
    content = await _read_upload(file)
    return service.commit(
        db, _client_id(user), file.filename or "upload", source, content, create_cards
    )


@router.get("/jobs", response_model=list[ImportJobOut])
def jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ImportJobOut]:
    return service.list_jobs(db, _client_id(user))
