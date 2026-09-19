"""Auth request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..models.user import Role


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.public
    organization: str | None = Field(default=None, max_length=160)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    organization: str | None = Field(default=None, max_length=160)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserAdminUpdate(UserUpdate):
    role: Role | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    """Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    role_label: str
    organization: str | None
    is_active: bool
    last_active_at: datetime | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageOut(BaseModel):
    detail: str
