"""Schemas auth & user (BLUEPRINT §20 — /auth/*, /me)."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

USERNAME_PATTERN = r"^[a-zA-Z0-9_.-]+$"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class VerifyRequest(BaseModel):
    token: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    email_verified: bool
    role: str
    locale: str
    base_currency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SessionOut(BaseModel):
    id: int
    device_name: str
    ip: str
    created_at: datetime
    last_seen_at: datetime | None
    is_current: bool = False

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UpdateMeRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    locale: str | None = Field(default=None, max_length=10)
    base_currency: str | None = Field(default=None, max_length=10)
