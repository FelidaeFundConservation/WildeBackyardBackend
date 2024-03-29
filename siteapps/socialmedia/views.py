import base64
import hashlib
import json
from io import BytesIO

import requests
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dateutil import parser
from django.conf import settings
from django.shortcuts import render
from PIL import Image
from rest_framework import authentication, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixins import LatLngValidationMixin, PostInputsValidationMixin, PrivacySettingValidationMixin
from .models import Media, MediaPost, TextComment

DATE_FORMAT = "%B %d, %Y %I:%M %p"


class GetRecentPostsView(APIView):
    def post(self, request):
        data = json.loads(request.body)

        # The center of the circle to check, if given
        user_latitude = data.get("userLatitude")
        user_longitude = data.get("userLongitude")

        # The radius of the circle to check for posts updates
        distance_radius = data.get("distance_radius")

        # A specific zip code to look for posts in
        zip_code = data.get("zipCode")

        post_data = []

        if user_latitude is None and user_longitude is None and zip_code is None:
            media_posts = MediaPost.objects.all().order_by("-created")[:10]

        for post in media_posts:
            location_info_fields = [
                post.geocoded_location_locality,
                post.geocoded_location_state,
                post.geocoded_location_country,
                post.geocoded_location_zip_code,
            ]
            geocoded_location = ", ".join(filter(None, location_info_fields))

            additional_data = {
                "camera_model": post.camera_model,
                "camera_deployment_date": post.camera_deployment_date,
                "camera_timestamp_offset_error_details": post.camera_timestamp_offset_error_details,
                "habitat_type": post.habitat_type,
            }

            media_data = (
                {
                    "url": post.media.file_cloud_path,
                    "is_video": post.media.is_video,
                }
                if post.media
                else None
            )

            current_data = {
                "id": post.id,
                "geoprivacy": post.geoprivacy,
                "created_by": post.created_by.name,
                "encounter_datetime": post.encounter_datetime,
                "research_use_allowed": post.research_use_allowed,
                "media": media_data,
                "additional_info": additional_data,
                "title": post.title,
                "body": post.text_content,
            }

            if post.geoprivacy == settings.PRIVACY_SETTING_PUBLIC:
                current_data.update(
                    {
                        "geocoded_location": geocoded_location,
                        "latitude": post.public_location_latitude,
                        "longitude": post.public_location_longitude,
                        "accuracy": post.accuracy_ring_radius_meters,
                    }
                )
            elif post.geoprivacy == settings.PRIVACY_SETTING_OBSCURED:
                current_data.update(
                    {
                        "geocoded_location": geocoded_location,
                        "obfuscation_range_kilometers": post.obfuscation_range_kilometers,
                        "corner_1_latitude": post.obfuscation_box_corner_1_latitude,
                        "corner_1_longitude": post.obfuscation_box_corner_1_longitude,
                        "corner_2_latitude": post.obfuscation_box_corner_2_latitude,
                        "corner_2_longitude": post.obfuscation_box_corner_2_longitude,
                        "corner_3_latitude": post.obfuscation_box_corner_3_latitude,
                        "corner_3_longitude": post.obfuscation_box_corner_3_longitude,
                        "corner_4_latitude": post.obfuscation_box_corner_4_latitude,
                        "corner_4_longitude": post.obfuscation_box_corner_4_longitude,
                    }
                )
            elif post.geoprivacy == settings.PRIVACY_SETTING_PRIVATE:
                # Don't send any location data for private.
                pass

            post_data.append(current_data)

        return Response(status=status.HTTP_200_OK, data=post_data)


# Create your views here.
class CreatePostView(APIView, LatLngValidationMixin, PrivacySettingValidationMixin, PostInputsValidationMixin):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        # No idea why this returns a list locally but not when deployed, but this'll fix that.
        if type(data) is list:
            data = data[0]

        # The image or video file (if any)
        media_bytes = data.get("mediaBytes")

        # Check if the media is a video
        is_video = data.get("isVideo")

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
        obfuscation_box_corners = {
            "obfuscation_box_corner_1_latitude": data.get("corner1Latitude"),
            "obfuscation_box_corner_1_longitude": data.get("corner1Longitude"),
            "obfuscation_box_corner_2_latitude": data.get("corner2Latitude"),
            "obfuscation_box_corner_2_longitude": data.get("corner2Longitude"),
            "obfuscation_box_corner_3_latitude": data.get("corner3Latitude"),
            "obfuscation_box_corner_3_longitude": data.get("corner3Longitude"),
            "obfuscation_box_corner_4_latitude": data.get("corner4Latitude"),
            "obfuscation_box_corner_4_longitude": data.get("corner4Longitude"),
        }

        # Argument validation
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
                title,
            ),
        ]

        for error_response in errors:
            if error_response is not None:
                return error_response

        kwargs = {
            "geoprivacy": privacy_setting,
            "encounter_datetime": parser.parse(encounter_datetime),
            "accuracy_ring_radius_meters": accuracy_meters,
            "geocoded_location_country": geocoded_location_country,
            "research_use_allowed": json.loads(research_use_allowed),
            "title": title,
        }

        # Set geoprivacy-specific keyword args
        if privacy_setting == settings.PRIVACY_SETTING_PUBLIC:
            kwargs["public_location_latitude"] = latitude
            kwargs["public_location_longitude"] = longitude
        elif privacy_setting == settings.PRIVACY_SETTING_OBSCURED:
            kwargs["true_location_latitude"] = latitude
            kwargs["true_location_longitude"] = longitude

            kwargs["obfuscation_range_kilometers"] = obfuscation_kilometers

            kwargs.update(obfuscation_box_corners)
        elif privacy_setting == settings.PRIVACY_SETTING_PRIVATE:
            kwargs["private_location_latitude"] = latitude
            kwargs["private_location_longitude"] = longitude

        # Set optional arguments

        # TODO: Handle creating the media object
        media_obj = None

        if media_bytes is not None:
            media_bytes = convert_base64_bytes(media_bytes, is_video=is_video)
            content_hash = hashlib.sha256(media_bytes).hexdigest()
            # Check if the file already exists
            if not Media.objects.filter(content_hash=content_hash).exists():
                if is_video is True:
                    media_obj = create_video_media(media_bytes=media_bytes, content_hash=content_hash, request=request)
                else:
                    media_obj = create_image_media(media_bytes=media_bytes, content_hash=content_hash, request=request)
            else:
                media_obj = Media.objects.get(content_hash=content_hash)

        if media_obj is not None:
            kwargs["media"] = media_obj

        if body is not None:
            kwargs["text_content"] = body
        if geocoded_location_locality is not None:
            kwargs["geocoded_location_locality"] = geocoded_location_locality
        if geocoded_location_state is not None:
            kwargs["geocoded_location_state"] = geocoded_location_state
        if geocoded_location_zip_code is not None:
            kwargs["geocoded_location_zip_code"] = geocoded_location_zip_code
        if camera_model is not None:
            kwargs["camera_model"] = camera_model
        if camera_deployment_date is not None:
            kwargs["camera_deployment_date"] = parser.parse(camera_deployment_date)
        if camera_timestamp_offset_error_details is not None:
            kwargs["camera_timestamp_offset_error_details"] = camera_timestamp_offset_error_details
        if habitat_type is not None:
            kwargs["habitat_type"] = habitat_type

        # Finally, create the post object with given args
        MediaPost.objects.create(**kwargs, created_by=request.user)

        return Response(status=status.HTTP_201_CREATED)


def convert_base64_bytes(media_bytes_base64, is_video=False):
    media_bytes_base64 = bytearray(base64.b64decode(media_bytes_base64))

    if is_video:
        return media_bytes_base64
    else:
        image = Image.open(BytesIO(media_bytes_base64))

        # Make the image into a thumbnail
        image.thumbnail(size=settings.PHOTO_MAX_SIZE)

        thumbnail_bytes_io = BytesIO()
        image.save(thumbnail_bytes_io, format="JPEG")
        thumbnail_bytes = thumbnail_bytes_io.getvalue()

        return thumbnail_bytes


def create_image_media(media_bytes, content_hash, request):
    blob_service_client = BlobServiceClient(
        account_url=f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/",
        credential=DefaultAzureCredential(),
    )
    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_STORAGE_CONTAINER_NAME, blob=f"{content_hash}.JPEG"
    )

    blob_client.upload_blob(media_bytes, blob_type="BlockBlob")

    return Media.objects.create(file_cloud_path=blob_client.url, content_hash=content_hash, uploaded_by=request.user)


def create_video_media(media_bytes):
    # TODO: Implement video upload.
    pass
