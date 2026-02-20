import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.views.generic import TemplateView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import authentication, permissions, serializers, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.socialmedia.mixins import check_profanity, createResponse400
from siteapps.socialmedia.models import MediaPost
from siteapps.users.models import User


# Serializers for API documentation
class UserProfileSerializer(serializers.Serializer):
    joined_date = serializers.CharField()
    display_name = serializers.CharField()
    sightings_count = serializers.IntegerField()
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()


class ChangeUsernameSerializer(serializers.Serializer):
    newUsername = serializers.CharField(min_length=3, help_text="New username (minimum 3 characters)")


class DeleteAccountSerializer(serializers.Serializer):
    confirmationString = serializers.CharField(help_text="User's current username for confirmation")


class EditStaffRoleSerializer(serializers.Serializer):
    accountEmail = serializers.EmailField(help_text="Email of the account to modify")
    setStaff = serializers.BooleanField(help_text="True to grant staff role, False to revoke")


class ApiErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


# Create your views here.
@extend_schema(
    summary="Get user profile",
    description="Retrieve the authenticated user's profile information including join date, display name, and sightings count",
    responses={
        200: UserProfileSerializer,
    },
    tags=["Users"],
)
class UserProfileView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "joined_date": request.user.created.strftime(settings.READABLE_DATE_FORMAT),
            "display_name": request.user.name,
            "sightings_count": MediaPost.objects.filter(created_by=request.user).count(),
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
        }

        return Response(status=status.HTTP_200_OK, data=data)


@extend_schema(
    summary="Change username",
    description="Update the authenticated user's display name",
    request=ChangeUsernameSerializer,
    responses={
        200: None,
        400: ApiErrorSerializer,
    },
    tags=["Users"],
)
class ChangeUsernameView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        new_username = data.get("newUsername")

        if len(new_username) < 3:
            message = "Username must be at least 3 characters long."

            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": message},
            )

        profanity_error = check_profanity(new_username)
        if profanity_error is not None:
            return profanity_error

        request.user.name = new_username
        request.user.save()

        return Response(status=status.HTTP_200_OK)


@extend_schema(
    summary="Delete account",
    description="Permanently delete the authenticated user's account. Requires username confirmation.",
    request=DeleteAccountSerializer,
    responses={
        200: None,
        400: ApiErrorSerializer,
    },
    tags=["Users"],
)
class DeleteAccountView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        confirmation_string = data.get("confirmationString")

        # Confirm user input to delete account
        if confirmation_string == self.request.user.name:
            self.request.user.delete()
            return Response(status=status.HTTP_200_OK)
        else:
            message = "The account deletion code was not input correctly."
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": message},
            )


# Give an account access to moderation tools. This is only callable from superuser accounts.
@extend_schema(
    summary="Edit staff role",
    description="Grant or revoke staff permissions for a user account. Only accessible by superusers.",
    request=EditStaffRoleSerializer,
    responses={
        200: None,
        400: ApiErrorSerializer,
        403: ApiErrorSerializer,
        404: ApiErrorSerializer,
    },
    tags=["Admin"],
)
class EditStaffRoleView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        if request.user.is_superuser:
            data = json.loads(request.body)

            account_email = data.get("accountEmail")
            # If true, assigns role, else revokes
            set_staff = data.get("setStaff")

            # Check arguments
            if not account_email:
                return createResponse400("The account email to grant/revoke staff membership was not provided.")
            if not set_staff:
                return createResponse400("Staff membership to change to was not provided.")

            # Grant or revoke staff for user
            try:
                user = User.objects.get(email=account_email)
                user.is_staff = set_staff
                user.save()
                return Response(status=status.HTTP_200_OK)
            except ObjectDoesNotExist:
                message = f"User with email {account_email} not found."
                return Response(
                    status=status.HTTP_404_NOT_FOUND,
                    data={"error": message},
                )
        else:
            message = "This account is not allowed to perform this operation."

            return Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"error": message},
            )


class AccountVerifiedView(TemplateView):
    template_name = "account/email_confirm.html"
