from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import BannedEmail, User


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    """Admin interface for User model"""

    # Fields to display in the user list
    list_display = (
        "email",
        "name",
        "is_staff",
        "is_superuser",
        "is_active",
        "warnings",
        "created",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "warnings")
    search_fields = ("email", "name")
    ordering = ("email",)

    # Fields to display on the user detail/edit page
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "bio")}),
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
