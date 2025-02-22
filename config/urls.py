"""wilde_backyard URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from siteapps.users.views import AccountVerifiedView

urlpatterns = [
    # path("", include(("home.urls", "home"), namespace="home")),
    path("", AccountVerifiedView.as_view(), name="home"),
    path("account/", include("allauth.urls")),
    path("account/password_reset/", include("django_rest_passwordreset.urls", namespace="password_reset")),
    path("admin/", admin.site.urls),
    path("users/", include(("users.urls", "users"), namespace="app_users")),
    path("socialmedia/", include(("socialmedia.urls", "socialmedia"), namespace="socialmedia")),
    path("species/", include(("species.urls", "species"), namespace="species")),
    path("mapbox/", include(("mapbox.urls", "mapbox"), namespace="mapbox")),
]
