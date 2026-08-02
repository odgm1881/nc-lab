"""Pydantic-схемы аутентификации."""

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_bcrypt_length(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Пароль не должен превышать 72 байта в UTF-8")
    return value


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""
    client_name: str = Field(description="Название организации клиента")
    inn: str | None = None

    _password_length = field_validator("password")(_validate_bcrypt_length)


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    _password_length = field_validator("password")(_validate_bcrypt_length)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    client_id: str | None = None

    model_config = {"from_attributes": True}
