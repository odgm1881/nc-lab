"""Pydantic-схемы аутентификации."""

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""
    client_name: str = Field(description="Название организации клиента")
    inn: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


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
