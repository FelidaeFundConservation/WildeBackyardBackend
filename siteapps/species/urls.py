from django.urls import path

from siteapps.species.views import GetSpeciesNamesView

urlpatterns = [
    path("api/names/get/", GetSpeciesNamesView.as_view(), name="get_species"),
]
