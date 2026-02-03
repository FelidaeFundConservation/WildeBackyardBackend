import json

import requests
from django.conf import settings
from django.shortcuts import render
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import authentication, permissions, serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .throttles import (
    GeocodePerDayThrottle,
    GeocodePerMinuteThrottle,
    SearchSuggestionsPerDayThrottle,
    SearchSuggestionsPerMinuteThrottle,
)


# Create your views here.
@extend_schema(
    summary="Get location search suggestions",
    description="Search for location suggestions using Mapbox API",
    request=inline_serializer(name="LocationSearchRequest", fields={"searchText": serializers.CharField()}),
    responses={200: inline_serializer(name="LocationSearchResponse", fields={"suggestions": serializers.ListField()})},
    tags=["Mapbox"],
)
class GetMapboxLocationSearchSuggestions(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SearchSuggestionsPerMinuteThrottle, SearchSuggestionsPerDayThrottle]

    def post(self, request):
        data = json.loads(request.body)

        search_text = data.get("searchText")

        # Check if Mapbox token is configured
        if not settings.MAPBOX_SECRET_TOKEN:
            return Response(
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
                data={"error": "Mapbox service is not configured"}
            )

        api_url = "https://api.mapbox.com/search/searchbox/v1/suggest?"

        try:
            response = requests.get(
                url=f"{api_url}q={search_text}&limit=4&access_token={settings.MAPBOX_SECRET_TOKEN}&session_token={request.user.id}&types=poi,address"
            )

            if response.status_code == 200:
                data = json.loads(response.content)

                # Last element of list is metadata, so it should be removed
                suggestions = [(location["name"], location["full_address"]) for location in data["suggestions"]]

                return Response(status=status.HTTP_200_OK, data={"suggestions": suggestions})
            else:
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except requests.exceptions.RequestException:
            # Handle connection errors (e.g., blocked API access)
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={"error": "Unable to reach Mapbox API"}
            )


@extend_schema(
    summary="Get geocode coordinates",
    description="Convert an address to coordinates using Mapbox API",
    request=inline_serializer(name="GeocodeRequest", fields={"address": serializers.CharField()}),
    responses={200: inline_serializer(name="GeocodeResponse", fields={"coordinates": serializers.ListField()})},
    tags=["Mapbox"],
)
class GetMapboxGeocode(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [GeocodePerMinuteThrottle, GeocodePerDayThrottle]

    def post(self, request):
        data = json.loads(request.body)

        address = data.get("address")
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        # Validate input - need either address OR both lat/lng
        if not address and (latitude is None or longitude is None):
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": "Either 'address' or both 'latitude' and 'longitude' are required"}
            )

        # Check if Mapbox token is configured
        if not settings.MAPBOX_SECRET_TOKEN:
            return Response(
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
                data={"error": "Mapbox service is not configured"}
            )

        api_url = "https://api.mapbox.com/search/geocode/v6/forward?"

        try:
            response = requests.get(url=f"{api_url}q={address}&limit=1&access_token={settings.MAPBOX_SECRET_TOKEN}")

            if response.status_code == 200:
                data = json.loads(response.content)
                coordinates = data["features"][0]["geometry"]["coordinates"]

                return Response(status=status.HTTP_200_OK, data={"coordinates": coordinates})
            else:
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except requests.exceptions.RequestException:
            # Handle connection errors (e.g., blocked API access)
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={"error": "Unable to reach Mapbox API"}
            )
