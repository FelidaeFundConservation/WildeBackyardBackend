# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Pydantic schemas for User model validation and serialization.

These schemas provide type-safe validation for API requests and responses.
They work alongside Django ORM models to ensure data integrity.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8, description="User password (minimum 8 characters)")

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com", "name": "John Doe", "password": "********"}}
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=10000)
    phone_number: Optional[str] = Field(None, max_length=25)

    model_config = ConfigDict(json_schema_extra={"example": {"name": "Jane Doe", "email": "newemail@example.com"}})


class UserResponse(UserBase):
    """Schema for user response data."""

    id: UUID
    date_joined: datetime
    is_active: bool
    is_staff: bool
    warnings: int
    is_volunteer: bool
    is_expert: bool
    phone_number: str
    bio: str
    created: datetime
    modified: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Allows Pydantic to work with Django ORM models
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "name": "John Doe",
                "date_joined": "2024-01-15T10:30:00",
                "is_active": True,
                "is_staff": False,
                "warnings": 0,
                "created": "2024-01-15T10:30:00",
                "modified": "2024-01-15T10:30:00",
            }
        },
    )


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list[UserResponse]


class BannedEmailBase(BaseModel):
    """Base schema for banned email."""

    email: EmailStr
    ban_reason: str = Field(max_length=800, default="")


class BannedEmailCreate(BannedEmailBase):
    """Schema for creating a banned email entry."""

    pass


class BannedEmailResponse(BannedEmailBase):
    """Schema for banned email response."""

    id: UUID
    created: datetime
    modified: datetime

    model_config = ConfigDict(from_attributes=True)
