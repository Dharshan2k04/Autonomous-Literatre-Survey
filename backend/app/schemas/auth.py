"""Auth schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---- Request schemas ----

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    refresh_token: str


# ---- Response schemas ----

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    avatar_url: str | None = None
    oauth_provider: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWithToken(BaseModel):
    user: UserResponse
    tokens: TokenResponse
