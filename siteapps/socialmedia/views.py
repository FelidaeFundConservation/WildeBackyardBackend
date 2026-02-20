import base64
import hashlib
import json
import logging
from io import BytesIO

import requests
import structlog
from dateutil import parser
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Func, Q
from drf_spectacular.utils import extend_schema, inline_serializer
from google.cloud import storage as gcs_storage
from PIL import Image
from rest_framework import authentication, permissions, serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.species.models import SpeciesName
from siteapps.users.models import BannedEmail

from .geo_utils import calculate_offset_coordinates, get_continental_us_center
from .mixins import LatLngValidationMixin, PostInputsValidationMixin, PrivacySettingValidationMixin, check_profanity, createResponse400
from .models import InappropriateContentReport, Media, MediaPost, TextComment

User = get_user_model()

# Use structlog for structured logging with automatic extra dict capture
logger = structlog.get_logger(__name__)


def generate_signed_url(gcs_path, expiration=3600):
    """Make GCS object publicly readable and return its URL.

    For PAP-enabled buckets, we can't generate signed URLs without a service account key.
    Instead, we make the object publicly readable (bypasses PAP for individual objects).

    Args:
        gcs_path: The full GCS path (e.g., 'https://storage.googleapis.com/bucket/path/to/file')
        expiration: Not used (kept for compatibility)

    Returns:
        Public GCS URL
    """
    try:
        # Extract bucket and blob name from URL
        if not gcs_path.startswith("https://storage.googleapis.com/"):
            return gcs_path

        path_parts = gcs_path.replace("https://storage.googleapis.com/", "").split("/", 1)
        if len(path_parts) < 2:
            return gcs_path

        bucket_name = path_parts[0]
        blob_name = path_parts[1]

        # Create GCS client and get the blob
        storage_client = gcs_storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Return the public URL (bucket has uniform access control)
        return blob.public_url

    except Exception as e:
        logging.error(f"Failed to make object public: {gcs_path}: {e}")
        return gcs_path


class Haversine(Func):
    function = "HAVING"
    template = "(6371 * acos(cos(radians(%(lat)s)) * cos(radians(%(lat_field)s)) * cos(radians(%(lng_field)s) - radians(%(lng)s)) + sin(radians(%(lat)s)) * sin(radians(%(lat_field)s))))"
    output_field = models.FloatField()


def serialize_post(post):
    """Serialize a single MediaPost to a dict with privacy-aware location handling.

    Used by GetRecentPostsView, GetPostsByBoundingBoxView, and GetPostByIdView so that
    the response format is identical regardless of how the post was retrieved.
    """
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

    media_data = None
    if post.media:
        media_url = post.media.file_cloud_path
        if media_url and media_url.startswith("https://storage.googleapis.com/"):
            media_url = generate_signed_url(media_url)
        media_data = {
            "url": media_url,
            "is_video": post.media.is_video,
        }

    data = {
        "id": post.id,
        "geoprivacy": post.geoprivacy,
        "created_by": getattr(post.created_by, "name", "Deleted User"),
        "encounter_datetime": post.encounter_datetime,
        "species": getattr(post.species, "name", None),
        "media": media_data,
        "additional_info": additional_data,
        "title": post.title,
        "body": post.text_content,
    }

    if post.geoprivacy == settings.PRIVACY_SETTING_PUBLIC:
        if post.true_location_spatial:
            data.update(
                {
                    "geocoded_location": geocoded_location,
                    "latitude": post.true_location_spatial.y,
                    "longitude": post.true_location_spatial.x,
                    "accuracy": post.accuracy_ring_radius_meters,
                }
            )
    elif post.geoprivacy == settings.PRIVACY_SETTING_OBSCURED:
        if post.true_location_spatial:
            offset_lat, offset_lon = calculate_offset_coordinates(
                post.true_location_spatial.y,
                post.true_location_spatial.x,
                post.obfuscation_range_kilometers,
            )
            data.update(
                {
                    "geocoded_location": geocoded_location,
                    "latitude": offset_lat,
                    "longitude": offset_lon,
                    "obfuscation_range_kilometers": post.obfuscation_range_kilometers,
                }
            )
    elif post.geoprivacy == settings.PRIVACY_SETTING_PRIVATE:
        center_lat, center_lon = get_continental_us_center()
        data.update(
            {
                "latitude": center_lat,
                "longitude": center_lon,
            }
        )

    return data


@extend_schema(
    summary="Get recent posts",
    description="Retrieve recent wildlife sighting posts with optional filtering by location, distance, or species",
    request=inline_serializer(
        name="GetRecentPostsRequest",
        fields={
            "userLatitude": serializers.FloatField(required=False),
            "userLongitude": serializers.FloatField(required=False),
            "distanceRadius": serializers.FloatField(required=False),
            "zipCode": serializers.CharField(required=False),
            "species": serializers.CharField(required=False),
            "userId": serializers.IntegerField(required=False),
        },
    ),
    responses={200: inline_serializer(name="PostListResponse", fields={"results": serializers.ListField()})},
    tags=["Social Media"],
)
class GetRecentPostsView(APIView, LatLngValidationMixin):
    def post(self, request):
        data = json.loads(request.body)

        # Log input parameters with full request body using structlog
        logger.info(
            "GetRecentPostsView: Request received",
            request_data=data,
            http_method=request.method,
            path=request.path,
        )

        # The center of the circle to check, if given
        user_latitude = data.get("userLatitude")
        user_longitude = data.get("userLongitude")

        # The radius of the circle to check for posts updates
        distance_radius = data.get("distanceRadius")

        # A specific zip code to look for posts in
        zip_code = data.get("zipCode")

        # A species to filter by
        species = data.get("species")

        # A user ID to filter by (for "my sightings")
        user_id = data.get("userId")

        # A specific user ID to filter by
        user_id = data.get("userId")

        post_data = []

        # Filter by zipcode
        if zip_code:
            media_posts = MediaPost.objects.filter(geocoded_location_zip_code=zip_code).order_by("-created")
        # Filter by distance
        elif user_latitude or user_longitude or distance_radius:
            # Argument validation
            errors = [
                LatLngValidationMixin.validate_latitude_longitude(user_latitude, user_longitude),
                (None if distance_radius is not None else createResponse400("No distance radius to search given.")),
            ]

            for error_response in errors:
                if error_response is not None:
                    return error_response

            # Use PostGIS ST_DWithin for efficient spatial index usage
            from django.contrib.gis.db.models.functions import Distance
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import D

            user_point = Point(user_longitude, user_latitude, srid=4326)

            # ST_DWithin with spheroid=True uses geography for accurate distance calculations
            # Distance must be specified using D() for proper unit conversion
            media_posts = (
                MediaPost.objects.filter(
                    true_location_spatial__isnull=False,
                )
                .annotate(distance=Distance("true_location_spatial", user_point, spheroid=True))
                .filter(distance__lte=D(km=distance_radius))
                .order_by("distance")
            )
        # If no arguments given, get global posts
        else:
            media_posts = MediaPost.objects.all().order_by("-created")

        # If a user ID was provided, filter by that user
        if user_id is not None:
            media_posts = media_posts.filter(created_by__id=user_id)

        # If a species was selected, only get posts of that species
        if species is not None:
            media_posts = media_posts.filter(species__name=species)

        # If a user ID was provided, only get posts by that user
        if user_id is not None:
            media_posts = media_posts.filter(created_by__id=user_id)

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

            media_data = None
            if post.media:
                media_url = post.media.file_cloud_path
                # Generate signed URL for GCS files
                if media_url and media_url.startswith("https://storage.googleapis.com/"):
                    media_url = generate_signed_url(media_url)

                media_data = {
                    "url": media_url,
                    "is_video": post.media.is_video,
                }

            current_data = {
                "id": post.id,
                "geoprivacy": post.geoprivacy,
                "created_by": getattr(post.created_by, "name", "Deleted User"),
                "encounter_datetime": post.encounter_datetime,
                "species": getattr(post.species, "name", None),
                "media": media_data,
                "additional_info": additional_data,
                "title": post.title,
                "body": post.text_content,
            }

            if post.geoprivacy == settings.PRIVACY_SETTING_PUBLIC:
                # Use true_location_spatial as the source field - no perturbation for public
                if post.true_location_spatial:
                    current_data.update(
                        {
                            "geocoded_location": geocoded_location,
                            "latitude": post.true_location_spatial.y,
                            "longitude": post.true_location_spatial.x,
                            "accuracy": post.accuracy_ring_radius_meters,
                        }
                    )
            elif post.geoprivacy == settings.PRIVACY_SETTING_OBSCURED:
                # Use true_location_spatial as source, perturb it randomly within obfuscationKilometers diameter
                if post.true_location_spatial:
                    offset_lat, offset_lon = calculate_offset_coordinates(
                        post.true_location_spatial.y,
                        post.true_location_spatial.x,
                        post.obfuscation_range_kilometers,
                    )
                    current_data.update(
                        {
                            "geocoded_location": geocoded_location,
                            "latitude": offset_lat,
                            "longitude": offset_lon,
                            "obfuscation_range_kilometers": post.obfuscation_range_kilometers,
                        }
                    )
            elif post.geoprivacy == settings.PRIVACY_SETTING_PRIVATE:
                # Return center of lower 48 states (continental US)
                center_lat, center_lon = get_continental_us_center()
                current_data.update(
                    {
                        "latitude": center_lat,
                        "longitude": center_lon,
                    }
                )

            post_data.append(current_data)

        # Create response
        response_data = paginator.get_paginated_response(post_data).data

        # Log response payload with full data using structlog
        logger.info(
            "GetRecentPostsView: Returning posts",
            response_data=response_data,
            post_count=len(post_data),
            has_next=paginator.get_next_link() is not None,
            has_previous=paginator.get_previous_link() is not None,
        )

        return Response(response_data)


@extend_schema(
    summary="Get posts by bounding box",
    description="Retrieve wildlife sighting posts within a geographic bounding box. Uses spatial index for efficient querying.",
    request=inline_serializer(
        name="GetPostsByBoundingBoxRequest",
        fields={
            "minLatitude": serializers.FloatField(required=True, help_text="Southern latitude boundary"),
            "maxLatitude": serializers.FloatField(required=True, help_text="Northern latitude boundary"),
            "minLongitude": serializers.FloatField(required=True, help_text="Western longitude boundary"),
            "maxLongitude": serializers.FloatField(required=True, help_text="Eastern longitude boundary"),
            "species": serializers.CharField(required=False, help_text="Filter by species name"),
            "userId": serializers.IntegerField(required=False, help_text="Filter by user ID"),
        },
    ),
    responses={200: inline_serializer(name="BoundingBoxPostListResponse", fields={"results": serializers.ListField()})},
    tags=["Social Media"],
)
class GetPostsByBoundingBoxView(APIView, LatLngValidationMixin):
    def post(self, request):
        data = json.loads(request.body)

        # Log input parameters with full request body using structlog
        logger.info(
            "GetPostsByBoundingBoxView: Request received",
            request_data=data,
            http_method=request.method,
            path=request.path,
        )

        # Extract bounding box parameters
        min_latitude = data.get("minLatitude")
        max_latitude = data.get("maxLatitude")
        min_longitude = data.get("minLongitude")
        max_longitude = data.get("maxLongitude")

        # Optional filters
        species = data.get("species")
        user_id = data.get("userId")

        # Validate required parameters
        if min_latitude is None or max_latitude is None or min_longitude is None or max_longitude is None:
            return Response(
                {
                    "error": "All bounding box parameters (minLatitude, maxLatitude, minLongitude, maxLongitude) are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate latitude ranges
        if not (-90 <= min_latitude <= 90) or not (-90 <= max_latitude <= 90):
            return Response(
                {"error": "Latitude values must be between -90 and 90."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate longitude ranges
        if not (-180 <= min_longitude <= 180) or not (-180 <= max_longitude <= 180):
            return Response(
                {"error": "Longitude values must be between -180 and 180."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate that min < max
        if min_latitude >= max_latitude:
            return Response(
                {"error": "minLatitude must be less than maxLatitude."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if min_longitude >= max_longitude:
            return Response(
                {"error": "minLongitude must be less than maxLongitude."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use PostGIS Polygon for bounding box query
        # This uses the spatial index (GIST) on true_location_spatial for efficient querying
        from django.contrib.gis.geos import Polygon

        # Create bounding box polygon: ((min_lng, min_lat), (max_lng, max_lat))
        bbox = Polygon.from_bbox((min_longitude, min_latitude, max_longitude, max_latitude))

        # Query with spatial index using __within or __contained
        # __contained uses the && operator which utilizes the spatial index
        # Exclude private sightings from bounding box queries
        media_posts = (
            MediaPost.objects.filter(
                true_location_spatial__isnull=False,
                true_location_spatial__contained=bbox,
            )
            .exclude(geoprivacy=settings.PRIVACY_SETTING_PRIVATE)
            .order_by("-created")
        )

        # Apply optional filters
        if user_id is not None:
            media_posts = media_posts.filter(created_by__id=user_id)

        if species is not None:
            media_posts = media_posts.filter(species__name=species)

        # Apply pagination
        paginator = LimitOffsetPagination()
        paginated_media_posts = paginator.paginate_queryset(media_posts, request)

        # Collect and format post information to send
        post_data = []
        for post in paginated_media_posts:
            # Skip private sightings (belt-and-suspenders check)
            if post.geoprivacy == settings.PRIVACY_SETTING_PRIVATE:
                continue

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

            media_data = None
            if post.media:
                media_url = post.media.file_cloud_path
                # Generate signed URL for GCS files
                if media_url and media_url.startswith("https://storage.googleapis.com/"):
                    media_url = generate_signed_url(media_url)

                media_data = {
                    "url": media_url,
                    "is_video": post.media.is_video,
                }

            current_data = {
                "id": post.id,
                "geoprivacy": post.geoprivacy,
                "created_by": getattr(post.created_by, "name", "Deleted User"),
                "encounter_datetime": post.encounter_datetime,
                "species": getattr(post.species, "name", None),
                "media": media_data,
                "additional_info": additional_data,
                "title": post.title,
                "body": post.text_content,
            }

            if post.geoprivacy == settings.PRIVACY_SETTING_PUBLIC:
                # Use true_location_spatial as the source field - no perturbation for public
                if post.true_location_spatial:
                    current_data.update(
                        {
                            "geocoded_location": geocoded_location,
                            "latitude": post.true_location_spatial.y,
                            "longitude": post.true_location_spatial.x,
                            "accuracy": post.accuracy_ring_radius_meters,
                        }
                    )
            elif post.geoprivacy == settings.PRIVACY_SETTING_OBSCURED:
                # Use true_location_spatial as source, perturb it randomly within obfuscationKilometers diameter
                if post.true_location_spatial:
                    offset_lat, offset_lon = calculate_offset_coordinates(
                        post.true_location_spatial.y,
                        post.true_location_spatial.x,
                        post.obfuscation_range_kilometers,
                    )
                    current_data.update(
                        {
                            "geocoded_location": geocoded_location,
                            "latitude": offset_lat,
                            "longitude": offset_lon,
                            "obfuscation_range_kilometers": post.obfuscation_range_kilometers,
                        }
                    )
            elif post.geoprivacy == settings.PRIVACY_SETTING_PRIVATE:
                # Return center of lower 48 states (continental US)
                center_lat, center_lon = get_continental_us_center()
                current_data.update(
                    {
                        "latitude": center_lat,
                        "longitude": center_lon,
                    }
                )

            post_data.append(current_data)

        # Create response
        response_data = paginator.get_paginated_response(post_data).data

        # Log response payload with full data using structlog
        logger.info(
            "GetPostsByBoundingBoxView: Returning posts",
            response_data=response_data,
            post_count=len(post_data),
            has_next=paginator.get_next_link() is not None,
            has_previous=paginator.get_previous_link() is not None,
            bbox_params={
                "minLat": min_latitude,
                "maxLat": max_latitude,
                "minLng": min_longitude,
                "maxLng": max_longitude,
            },
        )

        return Response(response_data)


@extend_schema(
    summary="Get a single post by ID",
    description="Retrieve a single wildlife sighting post by its UUID. Returns the same field set as the feed endpoints.",
    responses={
        200: inline_serializer(
            name="PostDetailByIdResponse",
            fields={
                "id": serializers.UUIDField(),
                "title": serializers.CharField(),
                "body": serializers.CharField(),
                "species": serializers.CharField(),
                "geoprivacy": serializers.CharField(),
                "created_by": serializers.CharField(),
                "encounter_datetime": serializers.DateTimeField(),
                "media": serializers.DictField(required=False),
                "additional_info": serializers.DictField(),
                "geocoded_location": serializers.CharField(required=False),
                "latitude": serializers.FloatField(required=False),
                "longitude": serializers.FloatField(required=False),
            },
        ),
        404: None,
    },
    tags=["Social Media"],
)
class GetPostByIdView(APIView):
    """Return a single post by UUID. Used by the web app detail page."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        logger.info("GetPostByIdView: returning post", post_id=str(post_id))
        return Response(serialize_post(post))


def check_post_is_liked_by(media_post_obj, user):
    return media_post_obj.upvoted_by.filter(id=user.id).exists()


def get_post_responses(request):
    data = json.loads(request.body)

    media_post_id = data.get("mediaPostId")
    page = data.get("page", 1)
    page_size = data.get("page_size", 10)

    if media_post_id is None:
        return Response(
            data={"error": "The media post ID to retrieve data was not provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    else:
        try:
            media_post_obj = MediaPost.objects.get(id=media_post_id)

            # Query all comments related to the post and order by creation date
            comments_query = media_post_obj.replies.order_by("-created")

            # Set up pagination for comments
            paginator = Paginator(comments_query, page_size)
            comments_page = paginator.get_page(page)

            # Serialize the paginated comments data with like information
            comments_data = []
            for comment in comments_page:
                comments_data.append(
                    {
                        "id": str(comment.id),
                        "created_by__name": (comment.created_by.name if comment.created_by else "Anonymous"),
                        "text_content": comment.text_content,
                        "created": (comment.created.isoformat() if comment.created else None),
                        "like_count": comment.upvoted_by.count(),
                        "liked_by_current_user": comment.upvoted_by.filter(id=request.user.id).exists(),
                    }
                )

            return Response(
                status=status.HTTP_200_OK,
                data={
                    "like_count": media_post_obj.upvoted_by.all().count(),
                    "liked_by_current_user": check_post_is_liked_by(media_post_obj=media_post_obj, user=request.user),
                    "comments": comments_data,
                    "total_pages": paginator.num_pages,
                    "current_page": comments_page.number,
                    "has_next": comments_page.has_next(),
                    "has_previous": comments_page.has_previous(),
                },
            )
        except MediaPost.DoesNotExist:
            return Response(
                data={"error": "Media post not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                data={"error": "An error occurred: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    summary="Get post responses (no auth)",
    description="Get comments and likes for a post without authentication",
    request=inline_serializer(
        name="GetPostResponsesRequest",
        fields={
            "mediaPostId": serializers.IntegerField(),
            "page": serializers.IntegerField(required=False),
            "page_size": serializers.IntegerField(required=False),
        },
    ),
    responses={
        200: inline_serializer(
            name="PostResponsesData",
            fields={
                "like_count": serializers.IntegerField(),
                "comments": serializers.ListField(),
            },
        )
    },
    tags=["Social Media"],
)
class GetPostResponsesNoAuthView(APIView):
    # For getting post data that may update frequently (i.e. likes and comments)
    def post(self, request):
        return get_post_responses(request)


@extend_schema(
    summary="Get post responses (authenticated)",
    description="Get comments and likes for a post with authentication to show if current user liked it",
    request=inline_serializer(
        name="GetPostResponsesAuthRequest",
        fields={
            "mediaPostId": serializers.IntegerField(),
            "page": serializers.IntegerField(required=False),
            "page_size": serializers.IntegerField(required=False),
        },
    ),
    responses={
        200: inline_serializer(
            name="PostResponsesAuthData",
            fields={
                "like_count": serializers.IntegerField(),
                "liked_by_current_user": serializers.BooleanField(),
                "comments": serializers.ListField(),
            },
        )
    },
    tags=["Social Media"],
)
class GetPostResponsesAuthenticatedView(APIView):
    # Authenticated endpoint tracks the user, so can check if user liked the post
    def post(self, request):
        return get_post_responses(request)


@extend_schema(
    summary="Like/unlike a post",
    description="Toggle like status on a media post",
    request=inline_serializer(name="LikePostRequest", fields={"mediaPostId": serializers.IntegerField()}),
    responses={200: None, 404: None},
    tags=["Social Media"],
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


@extend_schema(
    summary="Like/unlike a comment",
    description="Toggle like status on a comment",
    request=inline_serializer(name="LikeCommentRequest", fields={"commentId": serializers.CharField()}),
    responses={200: None, 404: None},
    tags=["Social Media"],
)
class LikeCommentView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        comment_id = data.get("commentId")

        if comment_id is None:
            return createResponse400("The comment ID to like/unlike was not provided.")
        else:
            try:
                comment_obj = TextComment.objects.get(id=comment_id)

                # Toggle the like status
                if comment_obj.upvoted_by.filter(id=request.user.id).exists():
                    comment_obj.upvoted_by.remove(request.user)
                    is_liked = False
                else:
                    comment_obj.upvoted_by.add(request.user)
                    is_liked = True

                return Response(
                    status=status.HTTP_200_OK,
                    data={
                        "status": "success",
                        "is_liked": is_liked,
                        "like_count": comment_obj.upvoted_by.count(),
                    },
                )

            except TextComment.DoesNotExist:
                return Response(
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Exception as e:
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    data={"error": str(e)},
                )


@extend_schema(
    summary="Create a comment",
    description="Add a comment to a media post",
    request=inline_serializer(
        name="CreateCommentRequest",
        fields={
            "parentPostId": serializers.IntegerField(),
            "commentText": serializers.CharField(),
        },
    ),
    responses={201: None, 400: None, 404: None, 405: None},
    tags=["Social Media"],
)
class CreateCommentView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        parent_post_id = data.get("parentPostId")
        comment_text = data.get("commentText")

        media_post = MediaPost.objects.filter(id=parent_post_id)

        # Check if user is banned
        if BannedEmail.objects.filter(email=request.user.email).exists():
            return Response(
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
                data={"error": "This account is not allowed to make comments."},
            )

        # Input validation
        if parent_post_id is None:
            return createResponse400("The post to reply to wasn't specified.")
        if not media_post.exists():
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={"error": f"Post with id {parent_post_id} wasn't found."},
            )
        if comment_text is None or len(comment_text) == 0:
            return createResponse400("The provided comment text is empty.")

        profanity_error = check_profanity(comment_text)
        if profanity_error is not None:
            return profanity_error

        # If everything's fine, create and add the comment
        media_post.first().replies.add(TextComment.objects.create(text_content=comment_text, created_by=request.user))

        return Response(status=status.HTTP_201_CREATED)


class PostViewValidation:
    @staticmethod
    def validate_data_and_permissions(data, request):
        # Check if data is a list and extract first element if necessary
        if isinstance(data, list):
            data = data[0]

        # Check if the user is banned from posting (only for authenticated users)
        if request.user.is_authenticated and BannedEmail.objects.filter(email=request.user.email).exists():
            return (
                Response(
                    status=status.HTTP_405_METHOD_NOT_ALLOWED,
                    data={"error": "This account is not allowed to make posts."},
                ),
                None,
            )

        return None, data

    @staticmethod
    def process_media(data, request):
        # The image or video file (if any)
        media_bytes = data.get("mediaBytes")
        # Check if the media is a video
        is_video = data.get("isVideo")
        logging.info(f"[VIDEO DEBUG] process_media: is_video={is_video}, has_media={media_bytes is not None}")

        # TODO: Handle creating the media object
        media_obj = None

        if media_bytes is not None:
            logging.info(f"[VIDEO DEBUG] Processing media, base64 length: {len(media_bytes)}")
            try:
                media_bytes = convert_base64_bytes(media_bytes, is_video=is_video)
                logging.info(f"[VIDEO DEBUG] Converted base64, bytes size: {len(media_bytes)}")
                content_hash = hashlib.sha256(media_bytes).hexdigest()
                logging.info(f"[VIDEO DEBUG] Content hash: {content_hash}")
                # Check if the file already exists
                if not Media.objects.filter(content_hash=content_hash).exists():
                    logging.info("[VIDEO DEBUG] No existing media, creating new...")
                    media_obj = create_media(
                        media_bytes=media_bytes,
                        content_hash=content_hash,
                        request=request,
                        is_video=is_video,
                    )
                else:
                    media_obj = Media.objects.get(content_hash=content_hash)
            except ValueError as e:
                # Re-raise validation errors (e.g., file too large)
                raise e
            except Exception as e:
                logging.error(f"Error processing media: {str(e)}")
                raise ValueError(f"Failed to process media file: {str(e)}")
        return media_obj

    @staticmethod
    def set_geoprivacy_kwargs(data, privacy_setting, kwargs):
        # Exact location of the encounter
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        # The length of one side of the box
        obfuscation_kilometers = data.get("obfuscationKilometers")

        # ALWAYS set true_location_spatial regardless of privacy setting
        if latitude is not None and longitude is not None:
            kwargs["true_location_spatial"] = Point(longitude, latitude, srid=4326)

        # Set geoprivacy-specific keyword args
        if privacy_setting == settings.PRIVACY_SETTING_PUBLIC:
            kwargs["public_location_latitude"] = latitude
            kwargs["public_location_longitude"] = longitude
        elif privacy_setting == settings.PRIVACY_SETTING_OBSCURED:
            kwargs["obfuscation_range_kilometers"] = obfuscation_kilometers

        # No need to return anything for validation
        return None

    @staticmethod
    def set_optional_kwargs(data, kwargs):
        body = data.get("postBody")

        # The name of the species the user selected
        species = data.get("species")

        # The saved locality, country, and zip code string of the location
        geocoded_location_locality = data.get("geocodedLocationLocality")
        geocoded_location_state = data.get("geocodedLocationState")
        # geocoded_location_country variable is retrieved but not currently used
        # geocoded_location_country = data.get("geocodedLocationCountry")
        geocoded_location_zip_code = data.get("geocodedLocationZipCode")

        # The brand and type of camera used to take the media (if any)
        camera_model = data.get("cameraModel")
        camera_deployment_date = data.get("cameraDeploymentDate")
        camera_timestamp_offset_error_details = data.get("timestampOffsetErrorDetails")

        habitat_type = data.get("habitatType")

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

    @staticmethod
    def validate_and_extract_data(data, request):
        # Extract required data
        encounter_datetime = data.get("encounterDatetime")
        privacy_setting = data.get("privacySetting")
        accuracy_meters = data.get("accuracyMeters")
        geocoded_location_country = data.get("geocodedLocationCountry")
        post_title = data.get("postTitle")

        # Validate arguments
        errors = [
            LatLngValidationMixin.validate_latitude_longitude(
                latitude=data.get("latitude"), longitude=data.get("longitude")
            ),
            PrivacySettingValidationMixin.validate_privacy_setting(privacy_setting),
            PostInputsValidationMixin.validate_arguments_exist(
                privacy_setting,
                encounter_datetime,
                accuracy_meters,
                data.get("obfuscationKilometers"),
                None,  # No longer validating obfuscation_box_corners
                geocoded_location_country,
                post_title,
            ),
            check_profanity(post_title),
            check_profanity(data.get("postBody")),
        ]
        for error_response in errors:
            if error_response is not None:
                return error_response, None

        # Prepare kwargs
        kwargs = {
            "geoprivacy": privacy_setting,
            "encounter_datetime": parser.parse(encounter_datetime),
            "accuracy_ring_radius_meters": accuracy_meters,
            "geocoded_location_country": geocoded_location_country,
            "title": post_title,
        }

        # Process media if available
        try:
            media_obj = PostViewValidation.process_media(data, request)
            if media_obj is not None:
                kwargs["media"] = media_obj
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST), None
        except Exception as e:
            logging.error(f"Unexpected error processing media: {str(e)}")
            return (
                Response(
                    {"error": "Failed to process media file"},
                    status=status.HTTP_400_BAD_REQUEST,
                ),
                None,
            )

        # Set geoprivacy and optional keyword arguments
        PostViewValidation.set_geoprivacy_kwargs(data, privacy_setting, kwargs)
        PostViewValidation.set_optional_kwargs(data, kwargs)

        return None, kwargs


@extend_schema(
    summary="Create a new post",
    description="Create a new wildlife sighting post with optional media, location, and species information. Authentication is optional - anonymous posts will have null creator.",
    request=inline_serializer(
        name="CreatePostRequest",
        fields={
            "postTitle": serializers.CharField(),
            "privacySetting": serializers.CharField(),
            "latitude": serializers.FloatField(),
            "longitude": serializers.FloatField(),
            "accuracyMeters": serializers.FloatField(),
            "encounterDatetime": serializers.DateTimeField(),
            "geocodedLocationCountry": serializers.CharField(),
            "species": serializers.CharField(required=False),
            "postBody": serializers.CharField(required=False),
            "mediaBytes": serializers.CharField(required=False),
            "isVideo": serializers.BooleanField(required=False),
            "userId": serializers.IntegerField(
                required=False,
                help_text="Authenticated staff only: specify user ID to create post on behalf of. Returns 403 if unauthenticated or non-staff.",
            ),
        },
    ),
    responses={201: None, 400: None, 403: None, 404: None, 405: None},
    tags=["Social Media"],
)
class CreatePostView(
    APIView,
    LatLngValidationMixin,
    PrivacySettingValidationMixin,
    PostInputsValidationMixin,
):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = []  # Allow unauthenticated access

    def post(self, request):
        data = json.loads(request.body)

        # Validate data and check permissions
        error_response, data = PostViewValidation.validate_data_and_permissions(data, request)
        if error_response:
            return error_response

        # Validate arguments
        error_response, kwargs = PostViewValidation.validate_and_extract_data(data, request)
        if error_response:
            return error_response

        # Handle optional userId field
        user_id = data.get("userId")
        if user_id is not None:
            # Only allow authenticated staff/admin users to create posts on behalf of others
            if not request.user.is_authenticated:
                return Response(
                    status=status.HTTP_403_FORBIDDEN,
                    data={
                        "error": "The userId parameter requires authentication. Please log in or omit this parameter."
                    },
                )
            if not request.user.is_staff:
                return Response(
                    status=status.HTTP_403_FORBIDDEN,
                    data={"error": "You do not have permission to create posts on behalf of other users."},
                )

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    status=status.HTTP_404_NOT_FOUND,
                    data={"error": "Invalid user specified."},
                )
            created_by_user = user
        else:
            # For non-userId requests: use authenticated user if available, otherwise None for anonymous posts
            created_by_user = request.user if request.user.is_authenticated else None

        # Finally, create the post object with given args, ignoring is a duplicate exists
        MediaPost.objects.get_or_create(**kwargs, created_by=created_by_user)

        return Response(status=status.HTTP_201_CREATED)


def convert_base64_bytes(media_bytes_base64, is_video=False):
    logging.info(f"[VIDEO DEBUG] convert_base64_bytes called with is_video={is_video}")
    media_bytes_base64 = bytearray(base64.b64decode(media_bytes_base64))
    logging.info(f"[VIDEO DEBUG] Decoded base64, size: {len(media_bytes_base64)} bytes")

    if is_video:
        # Basic video size validation - max 500MB
        max_video_size = getattr(settings, "MAX_VIDEO_SIZE_MB", 500) * 1024 * 1024
        logging.info(f"[VIDEO DEBUG] Video validation: size={len(media_bytes_base64)}, max={max_video_size}")
        if len(media_bytes_base64) > max_video_size:
            raise ValueError(f"Video file too large. Maximum size is {max_video_size / (1024*1024)}MB")
        logging.info("[VIDEO DEBUG] Video validated, returning bytearray")
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
    logging.info(f"[VIDEO DEBUG] create_media: is_video={is_video}, hash={content_hash}")
    logging.info(f"[VIDEO DEBUG] media_bytes type={type(media_bytes)}, size={len(media_bytes)}")
    # Detect video format from file signature (magic bytes)
    file_extension = "JPEG"
    content_type = "image/jpeg"

    if is_video:
        logging.info(f"[VIDEO DEBUG] Detecting video format, first 12 bytes: {media_bytes[:12].hex()}")
        # Check video format from magic bytes
        if (
            media_bytes[:4] == b"\x00\x00\x00\x18"
            or media_bytes[:4] == b"\x00\x00\x00\x1c"
            or media_bytes[:4] == b"\x00\x00\x00\x20"
        ):
            # MP4/M4V format (ftyp box)
            file_extension = "MP4"
            content_type = "video/mp4"
        elif media_bytes[:4] == b"\x1a\x45\xdf\xa3":
            # WebM/MKV format
            file_extension = "WEBM"
            content_type = "video/webm"
        elif media_bytes[:4] == b"RIFF" and media_bytes[8:12] == b"AVI ":
            # AVI format
            file_extension = "AVI"
            content_type = "video/x-msvideo"
        else:
            # Default to MP4 if format not recognized
            file_extension = "MP4"
            content_type = "video/mp4"
            logging.warning("Unknown video format, defaulting to MP4")

        logging.info(f"[VIDEO DEBUG] Format detected: {file_extension}, content_type: {content_type}")

    # Upload to Google Cloud Storage
    gcs_url = None
    try:
        logging.info(f"[VIDEO DEBUG] Starting GCS upload for is_video={is_video}")
        gcs_client = gcs_storage.Client()
        gcs_bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
        logging.info(f"[VIDEO DEBUG] GCS bucket: {settings.GCS_BUCKET_NAME}")

        # Determine the path based on media type
        gcs_path = (
            getattr(settings, "GCS_VIDEOS_PATH", "media/movies")
            if is_video
            else getattr(settings, "GCS_IMAGES_PATH", "media/images")
        )
        blob_name = f"{gcs_path}/{content_hash}.{file_extension}"
        logging.info(f"[VIDEO DEBUG] Blob name: {blob_name}")

        gcs_blob = gcs_bucket.blob(blob_name)
        # Convert bytearray to bytes if needed
        upload_data = bytes(media_bytes) if isinstance(media_bytes, bytearray) else media_bytes
        logging.info(
            f"[VIDEO DEBUG] Uploading: data_type={type(upload_data)}, size={len(upload_data)}, content_type={content_type}"
        )
        gcs_blob.upload_from_string(upload_data, content_type=content_type)
        gcs_url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{blob_name}"

        logging.info(f"Successfully uploaded media to GCS: {blob_name}")
        logging.info(f"[VIDEO DEBUG] GCS URL: {gcs_url}")
    except Exception as e:
        logging.error(f"Failed to upload media to GCS: {str(e)}")

    # Use GCS URL if available, otherwise use local path
    final_url = gcs_url or f"local://{content_hash}.{file_extension}"
    if not gcs_url:
        logging.warning(f"GCS upload failed, falling back to local path: {final_url}")
    logging.info(f"[VIDEO DEBUG] Final URL: {final_url}")

    return Media.objects.create(
        file_cloud_path=final_url,
        content_hash=content_hash,
        uploaded_by=request.user if request.user.is_authenticated else None,
        is_video=is_video,
    )


@extend_schema(
    summary="Edit an existing post",
    description="Update a wildlife sighting post (only by the post creator)",
    request=inline_serializer(
        name="EditPostRequest",
        fields={
            "postId": serializers.IntegerField(),
            "postTitle": serializers.CharField(),
            "privacySetting": serializers.CharField(),
            "latitude": serializers.FloatField(),
            "longitude": serializers.FloatField(),
            "accuracyMeters": serializers.FloatField(),
            "encounterDatetime": serializers.DateTimeField(),
            "geocodedLocationCountry": serializers.CharField(),
        },
    ),
    responses={200: None, 400: None, 403: None, 404: None},
    tags=["Social Media"],
)
class EditPostView(
    APIView,
    LatLngValidationMixin,
    PrivacySettingValidationMixin,
    PostInputsValidationMixin,
):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        # Validate data and check permissions
        error_response, data = PostViewValidation.validate_data_and_permissions(data, request)
        if error_response:
            return error_response

        # Check if the post exists and the user is the creator
        try:
            post = MediaPost.objects.get(id=data.get("postId"))
        except MediaPost.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={"error": "Post not found."})

        # Ensure the authenticated user is the one who created the post
        if post.created_by != request.user:
            return Response(
                status=status.HTTP_403_FORBIDDEN,
                data={"error": "You do not have permission to edit this post."},
            )

        error_response, kwargs = PostViewValidation.validate_and_extract_data(data, request)
        if error_response:
            return error_response

        # Update the post
        MediaPost.objects.filter(id=data.get("postId")).update(**kwargs)

        return Response(status=status.HTTP_200_OK)
