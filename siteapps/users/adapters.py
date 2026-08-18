# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.http import HttpRequest

from siteapps.license_constants import DEFAULT_LICENSE


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", False)

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Send users to the web app verification endpoint instead of backend host URLs."""
        web_app_url = getattr(settings, "WEB_APP_URL", "").rstrip("/")
        if web_app_url:
            return f"{web_app_url}/users/verify-email/{emailconfirmation.key}/"
        return super().get_email_confirmation_url(request, emailconfirmation)

    def save_user(self, request, user, form, commit=True):
        """Save user, copy the name field, and ensure default_license is set."""
        user = super().save_user(request, user, form, commit=False)
        data = form.cleaned_data
        name = data.get("name", "").strip()
        if name:
            user.name = name
        # Guarantee default_license is never NULL regardless of how the user was built
        if not user.default_license:
            user.default_license = DEFAULT_LICENSE
        if commit:
            user.save()
        return user
