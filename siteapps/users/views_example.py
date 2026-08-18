# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Example API views using Pydantic for validation.

This module demonstrates how to integrate Pydantic schemas with Django REST Framework
views for type-safe API endpoints.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .schemas import UserCreate, UserListResponse, UserResponse, UserUpdate

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user with Pydantic validation.

    POST /api/users/register/
    {
        "email": "user@example.com",
        "name": "John Doe",
        "password": "securepassword123"
    }
    """
    try:
        # Validate incoming data with Pydantic
        user_data = UserCreate(**request.data)

        # Check if user already exists
        if User.objects.filter(email=user_data.email).exists():
            return Response({"error": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # Create Django model instance
        user = User.objects.create_user(email=user_data.email, name=user_data.name, password=user_data.password)

        # Serialize response with Pydantic
        response_data = UserResponse.model_validate(user)
        return Response(response_data.model_dump(), status=status.HTTP_201_CREATED)

    except ValidationError as e:
        # Pydantic validation errors are automatically formatted
        return Response({"validation_errors": e.errors()}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_profile(request, user_id=None):
    """
    Get user profile by ID or current user.

    GET /api/users/profile/
    GET /api/users/profile/{user_id}/
    """
    try:
        if user_id:
            user = User.objects.get(id=user_id)
        else:
            user = request.user

        # Convert Django model to Pydantic schema
        response_data = UserResponse.model_validate(user)
        return Response(response_data.model_dump())

    except ObjectDoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """
    Update current user's profile.

    PATCH /api/users/profile/
    {
        "name": "Jane Doe",
        "email": "newemail@example.com"
    }
    """
    try:
        user = request.user

        # Validate update data with Pydantic
        update_data = UserUpdate(**request.data)

        # Update only provided fields (Pydantic excludes None values)
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(user, field, value)

        user.save()

        # Return updated user data
        response_data = UserResponse.model_validate(user)
        return Response(response_data.model_dump())

    except ValidationError as e:
        return Response({"validation_errors": e.errors()}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_users(request):
    """
    List all users with pagination.

    GET /api/users/
    """
    try:
        # Get query parameters
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))

        # Calculate pagination
        start = (page - 1) * page_size
        end = start + page_size

        # Get users
        users = User.objects.all()[start:end]
        total_count = User.objects.count()

        # Convert to Pydantic schemas
        user_responses = [UserResponse.model_validate(user) for user in users]

        # Create paginated response
        response_data = UserListResponse(
            count=total_count,
            next=f"/api/users/?page={page + 1}" if end < total_count else None,
            previous=f"/api/users/?page={page - 1}" if page > 1 else None,
            results=user_responses,
        )

        return Response(response_data.model_dump())

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user(request):
    """
    Delete current user account.

    DELETE /api/users/profile/
    """
    try:
        user = request.user
        user.is_active = False
        user.save()

        return Response({"message": "User account deactivated successfully"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# URL patterns to add to urls.py:
"""
from django.urls import path
from .views_example import (
    register_user,
    get_user_profile,
    update_user_profile,
    list_users,
    delete_user
)

urlpatterns = [
    path('register/', register_user, name='user-register'),
    path('profile/', get_user_profile, name='user-profile'),
    path('profile/<uuid:user_id>/', get_user_profile, name='user-profile-detail'),
    path('profile/update/', update_user_profile, name='user-profile-update'),
    path('', list_users, name='user-list'),
    path('profile/delete/', delete_user, name='user-delete'),
]
"""


# Example usage with Django Ninja (alternative to DRF):
"""
from ninja import NinjaAPI, Router
from .schemas import UserCreate, UserResponse

api = NinjaAPI()
router = Router()

@router.post("/register", response=UserResponse)
def register(request, data: UserCreate):
    '''
    Django Ninja automatically validates using Pydantic schemas
    and provides automatic OpenAPI documentation.
    '''
    user = User.objects.create_user(
        email=data.email,
        name=data.name,
        password=data.password
    )
    return user

api.add_router("/users/", router)
"""
