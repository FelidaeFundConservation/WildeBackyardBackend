import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.views.generic import TemplateView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer
from rest_framework import authentication, permissions, serializers, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.license_constants import LICENSE_CHOICES
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
            "id": str(request.user.id),
            "joined_date": request.user.created.strftime(settings.READABLE_DATE_FORMAT),
            "display_name": request.user.name,
            "sightings_count": MediaPost.objects.filter(created_by=request.user).count(),
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
            "is_developer": request.user.has_developer_access,
            "is_expert": request.user.is_expert,
            "default_license": request.user.default_license,
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


class EditDeveloperRoleSerializer(serializers.Serializer):
    accountEmail = serializers.EmailField(help_text="Email of the account to modify")
    setDeveloper = serializers.BooleanField(help_text="True to grant developer role, False to revoke")


@extend_schema(
    summary="Edit developer role",
    description=(
        "Grant or revoke the developer role for a user account. Only accessible by superusers. "
        "Staff and superusers are always considered developers regardless of this flag."
    ),
    request=EditDeveloperRoleSerializer,
    responses={
        200: None,
        400: ApiErrorSerializer,
        403: ApiErrorSerializer,
        404: ApiErrorSerializer,
    },
    tags=["Admin"],
)
class EditDeveloperRoleView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"error": "This account is not allowed to perform this operation."},
            )

        data = json.loads(request.body)
        account_email = data.get("accountEmail")
        set_developer = data.get("setDeveloper")

        if not account_email:
            return createResponse400("The account email was not provided.")
        if set_developer is None:
            return createResponse400("setDeveloper was not provided.")

        try:
            user = User.objects.get(email=account_email)
            user.is_developer = set_developer
            user.save()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={"error": f"User with email {account_email} not found."},
            )


@extend_schema(
    summary="Update default sighting license",
    description="Update the authenticated user's default license applied to new sightings and media.",
    request=inline_serializer(
        name="UpdateDefaultLicenseRequest",
        fields={"licenseCode": serializers.ChoiceField(choices=[c[0] for c in LICENSE_CHOICES])},
    ),
    responses={200: None, 400: ApiErrorSerializer},
    tags=["Users"],
)
class UpdateDefaultLicenseView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)
        license_code = data.get("licenseCode")

        valid_codes = {code for code, _ in LICENSE_CHOICES}
        if not license_code or license_code not in valid_codes:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": f"Invalid license code. Valid options are: {', '.join(sorted(valid_codes))}"},
            )

        request.user.default_license = license_code
        request.user.save()
        return Response(status=status.HTTP_200_OK)


# ── API Key management ────────────────────────────────────────────────────────


@extend_schema(
    summary="Create API key",
    description=(
        "Create a new API key linked to the authenticated user. "
        "The raw key is returned **once** in this response and cannot be retrieved again."
    ),
    request=inline_serializer(
        name="CreateAPIKeyRequest",
        fields={"name": serializers.CharField(help_text="Human-readable label for this key")},
    ),
    responses={
        201: inline_serializer(
            name="CreateAPIKeyResponse",
            fields={
                "prefix": serializers.CharField(),
                "name": serializers.CharField(),
                "api_key": serializers.CharField(help_text="Raw key — store this securely, shown only once"),
            },
        ),
        400: ApiErrorSerializer,
    },
    tags=["API Keys"],
)
class CreateUserAPIKeyView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from siteapps.users.models import UserAPIKey

        data = json.loads(request.body)
        name = data.get("name", "").strip()
        if not name:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "A key name is required."})

        api_key, key = UserAPIKey.objects.create_key(name=name, user=request.user)
        return Response(
            status=status.HTTP_201_CREATED,
            data={"prefix": api_key.prefix, "name": api_key.name, "api_key": key},
        )


@extend_schema(
    summary="List API keys",
    description="List all API keys belonging to the authenticated user.",
    responses={
        200: inline_serializer(
            name="APIKeyListItem",
            fields={
                "prefix": serializers.CharField(),
                "name": serializers.CharField(),
                "created": serializers.DateTimeField(),
                "revoked": serializers.BooleanField(),
                "expiry_date": serializers.DateTimeField(allow_null=True),
            },
            many=True,
        )
    },
    tags=["API Keys"],
)
class ListUserAPIKeysView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from siteapps.users.models import UserAPIKey

        keys = UserAPIKey.objects.filter(user=request.user).order_by("-created")
        data = [
            {
                "prefix": k.prefix,
                "name": k.name,
                "created": k.created,
                "revoked": k.revoked,
                "expiry_date": k.expiry_date,
            }
            for k in keys
        ]
        return Response(status=status.HTTP_200_OK, data=data)


@extend_schema(
    summary="Revoke API key",
    description="Revoke an API key owned by the authenticated user.",
    responses={
        200: None,
        403: ApiErrorSerializer,
        404: ApiErrorSerializer,
    },
    tags=["API Keys"],
)
class RevokeUserAPIKeyView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, prefix: str):
        from siteapps.users.models import UserAPIKey

        try:
            api_key = UserAPIKey.objects.get(prefix=prefix)
        except UserAPIKey.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={"error": "API key not found."})

        if api_key.user_id != request.user.pk:
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": "You do not own this API key."})

        api_key.revoked = True
        api_key.save()
        return Response(status=status.HTTP_200_OK)
