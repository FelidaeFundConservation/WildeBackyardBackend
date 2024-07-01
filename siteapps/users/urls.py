from allauth.account.views import PasswordChangeView
from dj_rest_auth.registration.views import RegisterView, ResendEmailVerificationView
from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView
from django.urls import path

from .views import ChangeUsernameView, DeleteAccountView, UserProfileView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="rest_register"),
    path("resend_verification_email/", ResendEmailVerificationView.as_view(), name="resend_email_confirmation"),
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("profile/change_username", ChangeUsernameView.as_view(), name="change_username"),
    path("delete_account", DeleteAccountView.as_view(), name="delete_account"),
]
