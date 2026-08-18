# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""URL configuration for habitat classification and GeoNames API."""

from django.urls import path

from . import views

app_name = "habitat"

urlpatterns = [
    # IUCN Habitat Classification
    path("api/query/", views.HabitatTypeByCoordinateView.as_view(), name="query_habitat"),
    # GeoNames Place Database
    path("api/geonames/nearest/", views.NearestPlaceView.as_view(), name="geonames_nearest"),
    path("api/geonames/search/", views.SearchPlacesView.as_view(), name="geonames_search"),
    path("api/geonames/place/<int:geonameid>/", views.PlaceDetailView.as_view(), name="geonames_detail"),
    # Postal Code Lookup (US ZIP + Canada Postal Codes)
    path("api/postalcode/lookup/", views.PostalCodeLookupView.as_view(), name="postalcode_lookup"),
    path("api/postalcode/search/", views.PostalCodeSearchView.as_view(), name="postalcode_search"),
    path("api/postalcode/nearby/", views.NearbyPostalCodesView.as_view(), name="postalcode_nearby"),
]
