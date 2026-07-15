"""API-слой аутентификации. Только HTTP."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> User:
    return service.register(db, data)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    return service.authenticate(db, data)


@router.post("/token", response_model=TokenOut, include_in_schema=False)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenOut:
    """Совместимость с OAuth2-формой Swagger (username = email)."""
    return service.authenticate(db, LoginIn(email=form.username, password=form.password))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
