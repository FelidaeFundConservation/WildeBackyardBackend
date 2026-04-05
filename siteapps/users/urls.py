from allauth.account.views import PasswordChangeView
from dj_rest_auth.registration.views import RegisterView, ResendEmailVerificationView
from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView
from django.urls import path

from .views import (
    AccountVerifiedView,
    ChangeUsernameView,
    CreateUserAPIKeyView,
    DeleteAccountView,
    EditDeveloperRoleView,
    EditStaffRoleView,
    ListUserAPIKeysView,
    RevokeUserAPIKeyView,
    UpdateDefaultLicenseView,
    UserProfileView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="rest_register"),
    path("resend_verification_email/", ResendEmailVerificationView.as_view(), name="resend_email_confirmation"),
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("profile/change_username", ChangeUsernameView.as_view(), name="change_username"),
    path("profile/update-default-license/", UpdateDefaultLicenseView.as_view(), name="update_default_license"),
    path("delete_account", DeleteAccountView.as_view(), name="delete_account"),
    path("edit_staff", EditStaffRoleView.as_view(), name="edit_staff"),
    path("edit_developer", EditDeveloperRoleView.as_view(), name="edit_developer"),
    # API key management
    path("api-keys/", ListUserAPIKeysView.as_view(), name="list_api_keys"),
    path("api-keys/create/", CreateUserAPIKeyView.as_view(), name="create_api_key"),
    path("api-keys/<str:prefix>/revoke/", RevokeUserAPIKeyView.as_view(), name="revoke_api_key"),
]
