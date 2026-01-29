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
        json_schema_extra={
            "example": {"email": "user@example.com", "name": "John Doe", "password": "securepassword123"}
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None

    model_config = ConfigDict(json_schema_extra={"example": {"name": "Jane Doe", "email": "newemail@example.com"}})


class UserResponse(UserBase):
    """Schema for user response data."""

    id: UUID
    date_joined: datetime
    is_active: bool
    is_staff: bool
    warnings: int
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


# Example usage in views:
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pydantic import ValidationError
from .models import User
from .schemas import UserCreate, UserResponse, UserUpdate

@api_view(['POST'])
def create_user(request):
    '''Create a new user with Pydantic validation.'''
    try:
        # Validate incoming data
        user_data = UserCreate(**request.data)

        # Create Django model instance
        user = User.objects.create_user(
            email=user_data.email,
            name=user_data.name,
            password=user_data.password
        )

        # Serialize response
        response = UserResponse.model_validate(user)
        return Response(response.model_dump(), status=status.HTTP_201_CREATED)

    except ValidationError as e:
        return Response({'errors': e.errors()}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_user(request, user_id):
    '''Get user by ID with Pydantic serialization.'''
    try:
        user = User.objects.get(id=user_id)
        response = UserResponse.model_validate(user)
        return Response(response.model_dump())
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH'])
def update_user(request, user_id):
    '''Update user with Pydantic validation.'''
    try:
        user = User.objects.get(id=user_id)

        # Validate update data
        update_data = UserUpdate(**request.data)

        # Update only provided fields
        if update_data.name is not None:
            user.name = update_data.name
        if update_data.email is not None:
            user.email = update_data.email

        user.save()

        # Return updated user
        response = UserResponse.model_validate(user)
        return Response(response.model_dump())

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({'errors': e.errors()}, status=status.HTTP_400_BAD_REQUEST)
"""
