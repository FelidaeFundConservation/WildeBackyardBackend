import base64
import hashlib
import json
import logging
from io import BytesIO

import requests
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dateutil import parser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Func, Q
from PIL import Image
from rest_framework import authentication, permissions, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.species.models import SpeciesName

from .mixins import LatLngValidationMixin, PostInputsValidationMixin, PrivacySettingValidationMixin, createResponse400
from .models import InappropriateContentReport, Media, MediaPost, TextComment


class Haversine(Func):
    function = "HAVING"
    template = "(6371 * acos(cos(radians(%(lat)s)) * cos(radians(%(lat_field)s)) * cos(radians(%(lng_field)s) - radians(%(lng)s)) + sin(radians(%(lat)s)) * sin(radians(%(lat_field)s))))"
    output_field = models.FloatField()


class GetRecentPostsView(APIView, LatLngValidationMixin):
    def post(self, request):
        data = json.loads(request.body)
        # The center of the circle to check, if given
        user_latitude = data.get("userLatitude")
        user_longitude = data.get("userLongitude")

        # The radius of the circle to check for posts updates
        distance_radius = data.get("distanceRadius")

        # A specific zip code to look for posts in
        zip_code = data.get("zipCode")

        # A species to filter by
        species = data.get("species")

        post_data = []

        # Filter by zipcode
        if zip_code:
            media_posts = MediaPost.objects.filter(geocoded_location_zip_code=zip_code).order_by("-created")
        # Filter by distance
        elif user_latitude or user_longitude or distance_radius:
            # Argument validation
            errors = [
                self.validate_latitude_longitude(user_latitude, user_longitude),
                None if distance_radius is not None else createResponse400("No distance radius to search given."),
            ]

            for error_response in errors:
                if error_response is not None:
                    return error_response

            media_posts = (
                MediaPost.objects.annotate(
                    distance_public=Haversine(
                        lat=user_latitude,
                        lng=user_longitude,
                        lat_field="public_location_latitude",
                        lng_field="public_location_longitude",
                    ),
                    distance_true=Haversine(
                        lat=user_latitude,
                        lng=user_longitude,
                        lat_field="true_location_latitude",
                        lng_field="true_location_longitude",
                    ),
                )
                .filter(Q(distance_public__lte=distance_radius) | Q(distance_true__lte=distance_radius))
                .order_by("-created")
            )
        # If no arguments given, get global posts
        else:
            media_posts = MediaPost.objects.all().order_by("-created")

        # If a species was selected, only get posts of that species
        if species is not None:
            media_posts = media_posts.filter(species__name=species)

        # Apply pagination
        paginator = LimitOffsetPagination()

        paginated_media_posts = paginator.paginate_queryset(media_posts, request)

        # Collect and format post information to send
        for post in paginated_media_posts:
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
                "created_by": getattr(post.created_by, "name", "Deleted User"),
                "encounter_datetime": post.encounter_datetime,
                "species": getattr(post.species, "name", None),
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
                # WARNING: Don't send true location for obscured.
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
                # WARNING: Don't send any location data for private.
                pass

            post_data.append(current_data)

        return paginator.get_paginated_response(post_data)


def check_post_is_liked_by(media_post_obj, user):
    return media_post_obj.upvoted_by.filter(id=user.id).exists()


def get_post_responses(request):
    data = json.loads(request.body)

    media_post_id = data.get("mediaPostId")

    if media_post_id is None:
        return createResponse400("The media post ID to retrieve data was not provided.")
    else:
        try:
            media_post_obj = MediaPost.objects.get(id=media_post_id)

            return Response(
                status=status.HTTP_200_OK,
                data={
                    "like_count": media_post_obj.upvoted_by.all().count(),
                    "liked_by_current_user": check_post_is_liked_by(media_post_obj=media_post_obj, user=request.user),
                    "comments": media_post_obj.replies.order_by("-created").values_list(
                        "created_by__name", "text_content", "created", "id"
                    ),
                },
            )
        except Exception:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
            )


class GetPostResponsesNoAuthView(APIView):
    # For getting post data that may update frequently (i.e. likes and comments)
    def post(self, request):
        return get_post_responses(request)


class GetPostResponsesAuthenticatedView(APIView):
    # Authenticated endpoint tracks the user, so can check if user liked the post
    def post(self, request):
        return get_post_responses(request)


class CreateInappropriateContentReport(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        content_id = data.get("contentId")
        content_type = data.get("contentType")

        report_kwargs = {
            "reported_by": request.user,
        }

        # Get the relevant comment/post object to report
        try:
            if content_type == "TextComment":
                report_kwargs["reported_comment"] = TextComment.objects.get(id=content_id)
            elif content_type == "MediaPost":
                report_kwargs["reported_post"] = MediaPost.objects.get(id=content_id)
            else:
                createResponse400("Invalid content type provided (must be either 'TextComment' or 'MediaPost.'")
        except ObjectDoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND, data={"error": f"Post or comment with id {content_id} wasn't found."}
            )

        # Create the report object if it doesn't exist
        InappropriateContentReport.objects.get_or_create(**report_kwargs)

        return Response(
            status=status.HTTP_201_CREATED,
        )


class LikePostView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        media_post_id = data.get("mediaPostId")

        if media_post_id is None:
            return createResponse400("The media post ID to like/unlike was not provided.")
        else:
            try:
                media_post_obj = MediaPost.objects.get(id=media_post_id)

                # Toggle the like status
                if check_post_is_liked_by(media_post_obj=media_post_obj, user=request.user):
                    media_post_obj.upvoted_by.remove(request.user)
                else:
                    media_post_obj.upvoted_by.add(request.user)

                return Response(
                    status=status.HTTP_200_OK,
                )

            except Exception:
                return Response(
                    status=status.HTTP_404_NOT_FOUND,
                )


class CreateCommentView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        parent_post_id = data.get("parentPostId")
        comment_text = data.get("commentText")

        media_post = MediaPost.objects.filter(id=parent_post_id)

        # Input validation
        if parent_post_id is None:
            return createResponse400("The post to reply to wasn't specified.")
        if not media_post.exists():
            return Response(
                status=status.HTTP_404_NOT_FOUND, data={"error": f"Post with id {parent_post_id} wasn't found."}
            )
        if comment_text is None or len(comment_text) == 0:
            return createResponse400("The provided comment text is empty.")

        # If everything's fine, create and add the comment
        media_post.first().replies.add(TextComment.objects.create(text_content=comment_text, created_by=request.user))

        return Response(status=status.HTTP_201_CREATED)


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

        # The name of the species the user selected
        species = data.get("species")

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
                media_obj = create_media(
                    media_bytes=media_bytes, content_hash=content_hash, request=request, is_video=is_video
                )
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
        if species is not None:
            try:
                kwargs["species"] = SpeciesName.objects.get(name=species)
            except Exception:
                logging.error(f"No species name found named {species}.")
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

        # .jpg doesn't support alpha channel, remove it if it exists.
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(thumbnail_bytes_io, format="JPEG")
        thumbnail_bytes = thumbnail_bytes_io.getvalue()

        return thumbnail_bytes


def create_media(media_bytes, content_hash, request, is_video=False):
    file_extension = "MP4" if is_video else "JPEG"

    blob_service_client = BlobServiceClient(
        account_url=f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/",
        credential=DefaultAzureCredential(),
    )

    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_STORAGE_CONTAINER_NAME, blob=f"{content_hash}.{file_extension}"
    )

    blob_client.upload_blob(media_bytes, blob_type="BlockBlob")

    return Media.objects.create(
        file_cloud_path=blob_client.url, content_hash=content_hash, uploaded_by=request.user, is_video=is_video
    )
