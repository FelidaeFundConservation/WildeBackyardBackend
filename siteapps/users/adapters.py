from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", False)

    def save_user(self, request, user, form, commit=True):
        """Save user and copy the name field from registration cleaned data."""
        user = super().save_user(request, user, form, commit=False)
        data = form.cleaned_data
        name = data.get("name", "").strip()
        if name:
            user.name = name
        if commit:
            user.save()
        return user
