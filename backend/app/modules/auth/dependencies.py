"""FastAPI-зависимости аутентификации: текущий пользователь и проверка роли."""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.database import get_db
from app.modules.auth import repository as repo
from app.modules.auth.models import ROLE_ADMIN, ROLE_OPERATOR, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise AuthError("Требуется авторизация.")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthError("Недействительный токен.")
    user = repo.get_user_by_id(db, payload["sub"])
    if user is None:
        raise AuthError("Пользователь не найден.")
    return user


def require_operator(user: User = Depends(get_current_user)) -> User:
    """Доступ только для оператора каталога или админа."""
    if user.role not in (ROLE_OPERATOR, ROLE_ADMIN):
        raise AuthError("Требуются права оператора.")
    return user
