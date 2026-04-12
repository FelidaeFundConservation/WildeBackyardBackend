"""URL configuration for habitat classification API."""

from django.urls import path

from . import views

app_name = "habitat"

urlpatterns = [
    path("api/query/", views.HabitatTypeByCoordinateView.as_view(), name="query_habitat"),
]
