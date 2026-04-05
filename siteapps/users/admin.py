from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from rest_framework_api_key.admin import APIKeyModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import BannedEmail, User, UserAPIKey

# Unregister allauth's EmailAddress model from admin to avoid duplication
# since email management is already handled in the User admin
try:
    from allauth.account.models import EmailAddress

    admin.site.unregister(EmailAddress)
except (admin.sites.NotRegistered, ImportError):
    # EmailAddress may not be registered or allauth may not be installed
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    """Admin interface for User model"""

    # Fields to display in the user list
    list_display = (
        "email",
        "name",
        "is_staff",
        "is_superuser",
        "is_developer",
        "is_active",
        "is_volunteer",
        "is_expert",
        "warnings",
        "created",
    )
    list_filter = ("is_staff", "is_superuser", "is_developer", "is_active", "is_volunteer", "is_expert", "warnings")
    search_fields = ("email", "name")
    ordering = ("email",)

    # Fields to display on the user detail/edit page
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "bio", "phone_number")}),
        ("Roles", {"fields": ("is_volunteer", "is_expert", "is_developer")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Moderation", {"fields": ("warnings",)}),
        ("Licensing", {"fields": ("default_license",)}),
        ("Important dates", {"fields": ("last_login", "created", "modified")}),
    )

    # Fields to display when adding a new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                ),
            },
        ),
    )

    readonly_fields = ("created", "modified", "last_login")
    filter_horizontal = ("groups", "user_permissions")


@admin.register(BannedEmail)
class BannedEmailAdmin(admin.ModelAdmin):
    """Admin interface for BannedEmail model"""

    list_display = ("email", "ban_reason", "created")
    search_fields = ("email", "ban_reason")
    readonly_fields = ("created", "modified")


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(APIKeyModelAdmin):
    """Admin interface for UserAPIKey model"""

    list_display = ("name", "user", "prefix", "created", "revoked", "expiry_date")
    list_filter = ("revoked",)
    search_fields = ("name", "prefix", "user__email", "user__name")
    raw_id_fields = ("user",)
