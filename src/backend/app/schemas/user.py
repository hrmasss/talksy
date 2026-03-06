"""User-related schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.base import BaseSchema, TimestampMixin
from pydantic import EmailStr, Field, field_validator


class UserCreate(BaseSchema):
    """Schema for creating a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    target_exam: str | None = Field(default=None, pattern="^(ielts|pte|toefl)$")
    target_score: float | None = Field(default=None, ge=0, le=9)
    timezone: str = "UTC"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating user information."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = None
    target_exam: str | None = Field(default=None, pattern="^(ielts|pte|toefl)$")
    target_score: float | None = Field(default=None, ge=0, le=9)
    timezone: str | None = None
    preferences: dict[str, Any] | None = None


class UserResponse(BaseSchema, TimestampMixin):
    """Schema for user response."""

    id: UUID
    email: str
    full_name: str
    avatar_url: str | None = None
    is_active: bool
    is_admin: bool
    is_verified: bool
    target_exam: str | None = None
    target_score: float | None = None
    timezone: str
    preferences: dict[str, Any] = {}
    last_login_at: datetime | None = None


class UserLogin(BaseSchema):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class PasswordChange(BaseSchema):
    """Schema for changing password."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
