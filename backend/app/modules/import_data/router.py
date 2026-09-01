"""API-слой импорта. Только HTTP. Загрузка файла multipart/form-data."""

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AuthError, DomainError, PayloadTooLargeError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user, require_editor
from app.modules.auth.models import User
from app.modules.import_data import service
from app.modules.import_data.schemas import (
    ImportCommitOut,
    ImportJobOut,
    ImportPreviewOut,
    ImportRowResultOut,
    MappingProfileIn,
    MappingProfileOut,
)

router = APIRouter()


def _client_id(user: User) -> str:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return user.client_id


def _read_upload(file: UploadFile) -> bytes:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm", ".xml"}:
        raise DomainError(
            "Разрешены только файлы CSV, XLSX, XLSM и XML.",
            code="UPLOAD_TYPE_NOT_ALLOWED",
        )
    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes / (1024 * 1024)
        raise PayloadTooLargeError(f"Размер файла превышает допустимый лимит {max_mb:g} МБ.")
    if suffix in {".xlsx", ".xlsm"}:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = archive.infolist()
                unpacked = sum(member.file_size for member in members)
                unpacked_limit = min(settings.max_upload_bytes * 20, 200 * 1024 * 1024)
                if len(members) > 2000 or unpacked > unpacked_limit:
                    raise PayloadTooLargeError(
                        "Распакованный Excel-файл превышает безопасный лимит."
                    )
        except zipfile.BadZipFile as exc:
            raise DomainError("Excel-файл повреждён.", code="IMPORT_PARSE_ERROR") from exc
    elif suffix == ".xml" and not content.lstrip().startswith(b"<"):
        raise DomainError("XML-файл повреждён.", code="IMPORT_PARSE_ERROR")
    elif suffix == ".csv" and b"\x00" in content:
        raise DomainError(
            "CSV-файл содержит недопустимые бинарные данные.",
            code="IMPORT_PARSE_ERROR",
        )
    return content


@router.post("/preview", response_model=ImportPreviewOut)
def preview(
    file: UploadFile = File(...),
    source: str | None = Form(None),
    profile_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> ImportPreviewOut:
    """Распарсить и показать нормализованную номенклатуру без сохранения."""
    content = _read_upload(file)
    client_id = _client_id(user)
    profile = service.get_profile(db, client_id, profile_id)
    return service.preview(
        file.filename or "upload", source, content, profile.mapping if profile else None
    )


@router.post("/commit", response_model=ImportCommitOut, status_code=201)
def commit(
    file: UploadFile = File(...),
    source: str | None = Form(None),
    create_cards: bool = Form(True),
    profile_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> ImportCommitOut:
    """Сохранить файл, создать задание импорта и карточки-черновики."""
    content = _read_upload(file)
    client_id = _client_id(user)
    profile = service.get_profile(db, client_id, profile_id)
    return service.commit(
        db,
        client_id,
        file.filename or "upload",
        source,
        content,
        create_cards,
        profile.mapping if profile else None,
        user.id,
    )


@router.get("/jobs", response_model=list[ImportJobOut])
def jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ImportJobOut]:
    return service.list_jobs(db, _client_id(user))


@router.get("/jobs/{job_id}/rows", response_model=list[ImportRowResultOut])
def job_rows(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ImportRowResultOut]:
    return service.list_row_results(db, _client_id(user), job_id)


@router.get("/jobs/{job_id}/error-report")
def download_error_report(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    content = service.error_report(db, _client_id(user), job_id, user.id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="import-errors.csv"'},
    )


@router.get("/mapping-profiles", response_model=list[MappingProfileOut])
def mapping_profiles(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MappingProfileOut]:
    return service.list_profiles(db, _client_id(user))


@router.post("/mapping-profiles", response_model=MappingProfileOut, status_code=201)
def create_mapping_profile(
    data: MappingProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> MappingProfileOut:
    return service.create_profile(db, _client_id(user), data, user.id)


@router.delete("/mapping-profiles/{profile_id}", status_code=204)
def delete_mapping_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_editor),
) -> None:
    service.delete_profile(db, _client_id(user), profile_id, user.id)
