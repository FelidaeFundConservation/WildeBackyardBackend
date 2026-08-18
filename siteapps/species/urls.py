# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
from django.urls import path

from siteapps.species.views import CreateSpeciesNameView, GetSpeciesNamesView, GetTaxaView

urlpatterns = [
    path("api/names/get/", GetSpeciesNamesView.as_view(), name="get_species"),
    path("api/names/create/", CreateSpeciesNameView.as_view(), name="create_species"),
    path("api/taxa/", GetTaxaView.as_view(), name="get_taxa"),
]
