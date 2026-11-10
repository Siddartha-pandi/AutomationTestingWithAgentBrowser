"""Pydantic request and response schemas for authentication and RBAC."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """User credentials for authentication."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    """New user registration payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)


class RoleResponse(BaseModel):
    """Role definition with associated granular permissions."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    """Public user profile with assigned roles."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    roles: list[RoleResponse] = Field(default_factory=list)
    created_at: datetime


class TokenResponse(BaseModel):
    """RFC-compliant authentication response."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


class AssignRoleRequest(BaseModel):
    """Request to assign an RBAC role to a user."""

    role_name: str = Field(pattern="^(owner|admin|developer|tester|viewer)$")
