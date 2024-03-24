import json

import requests
from django.shortcuts import render
from rest_framework import authentication, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.socialmedia.mixins import LatLngValidationMixin, PostInputsValidationMixin, PrivacySettingValidationMixin


# Create your views here.
class CreatePostView(APIView, LatLngValidationMixin, PrivacySettingValidationMixin, PostInputsValidationMixin):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        # The image or video file (if any)
        media_bytes = data.get("mediaBytes")

        # Whether the user has opted for public, obfuscated, or private
        privacy_setting = data.get("privacySetting")

        # The time and date the encounter occured
        encounter_datetime = data.get("encounterDatetime")

        # Exact location of the encounter
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        # A circle radius where the true location may be in
        accuracy_meters = data.get("accuracyMeters")

        # The length of one side of the box
        obfuscation_kilometers = data.get("obfuscationKilometers")
        # This is a list of 4 points creating an offset box from the true point,
        # to obscure the true location from the public. Used in obfuscation mode.
        obfuscation_box_corners = data.get("obfuscationBoxCorners")

        # The saved locality, country, and zip code string of the location
        geocoded_location_locality = data.get("geocodedLocationLocality")
        geocoded_location_state = data.get("geocodedLocationState")
        geocoded_location_country = data.get("geocodedLocationCountry")
        geocoded_location_zip_code = data.get("geocodedLocationZipCode")

        # Text content
        title = data.get("postTitle")
        body = data.get("postBody")

        # Whether the user allowed public research usage
        research_use_allowed = data.get("researchUseAllowed")

        # The brand and type of camera used to take the media (if any)
        camera_model = data.get("cameraModel")
        camera_deployment_date = data.get("cameraDeploymentDate")
        camera_timestamp_offset_error_details = data.get("timestampOffsetErrorDetails")

        habitat_type = data.get("habitatType")

        # 4 corners of the obfuscation box, if given
        obfuscation_box_corners = [
            data.get("corner1Latitude"),
            data.get("corner1Longitude"),
            data.get("corner2Latitude"),
            data.get("corner2Longitude"),
            data.get("corner3Latitude"),
            data.get("corner3Longitude"),
            data.get("corner4Latitude"),
            data.get("corner4Longitude"),
        ]

        # Begin validation
        errors = [
            self.validate_latitude_longitude(latitude, longitude),
            self.validate_privacy_setting(privacy_setting),
            self.validate_arguments_exist(
                privacy_setting,
                encounter_datetime,
                accuracy_meters,
                obfuscation_kilometers,
                obfuscation_box_corners,
                geocoded_location_country,
                research_use_allowed,
            ),
        ]

        for error_response in errors:
            if error_response is not None:
                return error_response

        # TODO: Handle creating the object
        create_media()

        return Response(status=status.HTTP_201_CREATED)


def create_media():
    pass
