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
from django.db import connection, models
from django.db.models import Func, Q
from drf_spectacular.utils import extend_schema, inline_serializer
from google.cloud import storage as gcs_storage
from PIL import Image
from rest_framework import authentication, permissions, serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.license_constants import LICENSE_CHOICES, LICENSE_REQUIRES_ATTRIBUTION, LICENSE_SHORT_LABELS, LICENSE_URLS
from siteapps.species.models import SpeciesName, Taxon
from siteapps.users.models import BannedEmail

from .geo_utils import calculate_offset_coordinates, get_continental_us_center
from .mixins import LatLngValidationMixin, PostInputsValidationMixin, PrivacySettingValidationMixin, createResponse400
from .models import (
    InappropriateContentReport,
    IUCNHabitatClassification,
    Media,
    MediaPost,
    PostQualityMetric,
    SightingSpecies,
    SiteConfiguration,
    TextComment,
    UserSightingLocation,
)

User = get_user_model()

# Some early records were saved with the Django choice-tuple key ("1"/"2"/"3")
# instead of the human-readable value ("public"/"obscured"/"private").
# Normalise before any geoprivacy comparison.
_GEOPRIVACY_CODES: dict[str, str] = {
    "1": "public",  # settings.PRIVACY_SETTING_PUBLIC
    "2": "obscured",  # settings.PRIVACY_SETTING_OBSCURED
    "3": "private",  # settings.PRIVACY_SETTING_PRIVATE
}

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


def serialize_post(post, user=None, include_quality_metrics=False):
    """Serialize a single MediaPost to a dict with privacy-aware location handling.

    Used by GetRecentPostsView, GetPostsByBoundingBoxView, and GetPostByIdView so that
    the response format is identical regardless of how the post was retrieved.

    Args:
        post: MediaPost instance
        user: Optional authenticated User — when provided, user_vote is populated
              in quality_metrics (only relevant when include_quality_metrics=True)
        include_quality_metrics: When True, attach per-metric aggregates to the
                                  response (used on single-post detail views only)
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
        "iucn_habitat_lvl1_code": post.iucn_habitat_lvl1.code if post.iucn_habitat_lvl1 else None,
        "iucn_habitat_lvl1_name": post.iucn_habitat_lvl1.name if post.iucn_habitat_lvl1 else None,
        "iucn_habitat_lvl2_code": post.iucn_habitat_lvl2.code if post.iucn_habitat_lvl2 else None,
        "iucn_habitat_lvl2_name": post.iucn_habitat_lvl2.name if post.iucn_habitat_lvl2 else None,
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
        "quality_grade": post.quality_grade,
        "num_identification_agreements": post.num_identification_agreements,
        "num_identification_disagreements": post.num_identification_disagreements,
        "animal_count": post.animal_count,
        "license": {
            "code": post.license_code,
            "label": LICENSE_SHORT_LABELS.get(post.license_code, post.license_code),
            "url": LICENSE_URLS.get(post.license_code, ""),
            "attribution": post.attribution_override or getattr(post.created_by, "name", "Anonymous"),
            "requires_attribution": LICENSE_REQUIRES_ATTRIBUTION.get(post.license_code, True),
        },
        "speciesnet_predictions": post.speciesnet_predictions,
    }

    # Build ordered species list from SightingSpecies (prefer taxon; fall back to SpeciesName)
    sighting_species_qs = post.sighting_species.select_related("species", "taxon").order_by("rank")
    if sighting_species_qs.exists():
        species_list = []
        for ss in sighting_species_qs:
            if ss.taxon:
                species_list.append(ss.taxon.preferred_common_name or ss.taxon.name)
            elif ss.species:
                species_list.append(ss.species.name)
        data["species_list"] = species_list

        taxa_list = []
        for ss in sighting_species_qs:
            if ss.taxon:
                taxa_list.append(
                    {
                        "id": ss.taxon.id,
                        "inat_id": ss.taxon.inat_id,
                        "name": ss.taxon.name,
                        "preferred_common_name": ss.taxon.preferred_common_name,
                        "iconic_taxon_name": ss.taxon.iconic_taxon_name,
                        "default_photo_url": ss.taxon.default_photo_url,
                    }
                )
            else:
                taxa_list.append(None)
        data["taxa_list"] = taxa_list
    elif post.taxon:
        common = post.taxon.preferred_common_name or post.taxon.name
        data["species_list"] = [common]
        data["taxa_list"] = [
            {
                "id": post.taxon.id,
                "inat_id": post.taxon.inat_id,
                "name": post.taxon.name,
                "preferred_common_name": post.taxon.preferred_common_name,
                "iconic_taxon_name": post.taxon.iconic_taxon_name,
                "default_photo_url": post.taxon.default_photo_url,
            }
        ]
    elif post.species:
        data["species_list"] = [post.species.name]
        data["taxa_list"] = [None]
    else:
        data["species_list"] = []
        data["taxa_list"] = []

    if include_quality_metrics:
        # Derived quality criteria — computed from post data, not user votes
        has_location = post.true_location_spatial is not None or (
            post.public_location_latitude is not None and post.public_location_longitude is not None
        )
        data["quality_flags"] = {
            "date_specified": post.encounter_datetime is not None,
            "location_specified": has_location,
            "has_media": post.media is not None,
            "id_supported_by_two_or_more": post.num_identification_agreements >= 2,
        }

        # Community-voted quality metrics
        quality_metrics_data = []
        for metric in PostQualityMetric.METRICS:
            metric_votes = post.quality_metrics.filter(metric=metric)
            user_vote = None
            if user and user.is_authenticated:
                vote = metric_votes.filter(user=user).first()
                if vote is not None:
                    user_vote = vote.agree
            quality_metrics_data.append(
                {
                    "metric": metric,
                    "question": PostQualityMetric.METRIC_QUESTIONS[metric],
                    "agree_count": metric_votes.filter(agree=True).count(),
                    "disagree_count": metric_votes.filter(agree=False).count(),
                    "user_vote": user_vote,
                }
            )
        data["quality_metrics"] = quality_metrics_data

    # Normalise legacy integer-code geoprivacy values before comparison
    geoprivacy = _GEOPRIVACY_CODES.get(post.geoprivacy, post.geoprivacy)

    if geoprivacy == settings.PRIVACY_SETTING_PUBLIC:
        if post.true_location_spatial:
            data.update(
                {
                    "geocoded_location": geocoded_location,
                    "latitude": post.true_location_spatial.y,
                    "longitude": post.true_location_spatial.x,
                    "accuracy": post.accuracy_ring_radius_meters,
                }
            )
    elif geoprivacy == settings.PRIVACY_SETTING_OBSCURED:
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
    elif geoprivacy == settings.PRIVACY_SETTING_PRIVATE:
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
            "zipCode": serializers.CharField(required=False, help_text="ZIP/postal code (string match)"),
            "zipCodeBoundary": serializers.CharField(required=False, help_text="ZIP code for spatial boundary query"),
            "zipCodeCountry": serializers.CharField(
                required=False, help_text="Country code (US/CA) for zipCodeBoundary"
            ),
            "placeName": serializers.CharField(required=False, help_text="Place name for geographic lookup"),
            "placeCountry": serializers.CharField(required=False, help_text="Country code for place name lookup"),
            "placeRadius": serializers.FloatField(required=False, help_text="Radius in km around place (default 10)"),
            "species": serializers.CharField(required=False),
            "userId": serializers.UUIDField(required=False),
            "userDisplayName": serializers.CharField(required=False),
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

        # A specific zip code to look for posts in (string match on geocoded field)
        zip_code = data.get("zipCode")

        # Spatial query parameters - ZIP code boundary polygon
        zip_code_boundary = data.get("zipCodeBoundary")
        zip_code_country = data.get("zipCodeCountry", "US").upper()

        # Spatial query parameters - Place name lookup with radius
        place_name = data.get("placeName")
        place_country = data.get("placeCountry", "").upper()
        place_radius = data.get("placeRadius", 10.0)  # Default 10km

        # A species to filter by
        species = data.get("species")

        # A user ID to filter by (for "my sightings")
        user_id = data.get("userId")

        # A display name to filter by (for "another user")
        user_display_name = data.get("userDisplayName")

        # Verification filter: "verified" (>=2 agreements), "unverified" (<2), or "all" (default)
        verification_filter = data.get("verificationFilter", "all")

        post_data = []

        # Filter by ZIP code boundary polygon (spatial containment)
        if zip_code_boundary:
            from django.db import connection as db_connection

            # Normalize ZIP code
            zip_lookup = zip_code_boundary.strip().upper()
            if zip_code_country == "US":
                zip_lookup = zip_lookup.replace("-", "")[:5]

            # Look up ZIP code boundary in postal_codes table
            with db_connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT boundary, latitude, longitude, place_name
                    FROM postal_codes
                    WHERE postal_code = %s AND country = %s AND boundary IS NOT NULL
                    LIMIT 1
                    """,
                    [zip_lookup, zip_code_country],
                )
                zip_row = cursor.fetchone()

            if not zip_row:
                return Response(
                    {
                        "error": f"ZIP/postal code '{zip_code_boundary}' not found in {zip_code_country} or has no boundary data. Try using 'zipCode' parameter for string matching instead."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Filter sightings within ZIP code boundary using PostGIS ST_Contains
            media_posts = (
                MediaPost.objects.filter(
                    true_location_spatial__isnull=False,
                )
                .extra(
                    where=[
                        """
                        ST_Contains(
                            (SELECT boundary FROM postal_codes
                             WHERE postal_code = %s AND country = %s LIMIT 1),
                            true_location_spatial
                        )
                        """
                    ],
                    params=[zip_lookup, zip_code_country],
                )
                .order_by("-created")
            )

            logger.info(
                "Filtering by ZIP boundary",
                zip_code=zip_lookup,
                country=zip_code_country,
                place_name=zip_row[3],
            )

        # Filter by place name (lookup in geonames, then radius search)
        elif place_name:
            from django.contrib.gis.db.models.functions import Distance
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import D
            from django.db import connection as db_connection

            # Look up place in geonames table
            with db_connection.cursor() as cursor:
                if place_country:
                    cursor.execute(
                        """
                        SELECT geonameid, name, latitude, longitude, admin1, country, population
                        FROM geonames
                        WHERE name ILIKE %s AND country = %s
                        ORDER BY population DESC NULLS LAST
                        LIMIT 1
                        """,
                        [place_name, place_country],
                    )
                else:
                    cursor.execute(
                        """
                        SELECT geonameid, name, latitude, longitude, admin1, country, population
                        FROM geonames
                        WHERE name ILIKE %s
                        ORDER BY population DESC NULLS LAST
                        LIMIT 1
                        """,
                        [place_name],
                    )
                place_row = cursor.fetchone()

            if not place_row:
                country_msg = f" in {place_country}" if place_country else ""
                return Response(
                    {
                        "error": f"Place name '{place_name}' not found{country_msg}. Please check spelling or try a nearby city."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            place_lat = float(place_row[2])
            place_lon = float(place_row[3])
            place_point = Point(place_lon, place_lat, srid=4326)

            # Use radius search around the place
            media_posts = (
                MediaPost.objects.filter(
                    true_location_spatial__isnull=False,
                )
                .annotate(distance=Distance("true_location_spatial", place_point, spheroid=True))
                .filter(distance__lte=D(km=place_radius))
                .order_by("distance")
            )

            logger.info(
                "Filtering by place name",
                place_name=place_row[1],
                geonameid=place_row[0],
                lat=place_lat,
                lon=place_lon,
                radius_km=place_radius,
                country=place_row[5],
            )

        # Filter by zipcode (legacy string match)
        elif zip_code:
            media_posts = MediaPost.objects.filter(geocoded_location_zip_code=zip_code).order_by("-created")
        # Filter by distance (user-provided coordinates)
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

        # If a list of specific post IDs was provided, filter to those posts only
        post_ids = data.get("postIds")
        if post_ids:
            media_posts = media_posts.filter(id__in=post_ids)

        # If a display name was provided, filter by that user's name
        if user_display_name:
            media_posts = media_posts.filter(created_by__name__icontains=user_display_name)

        # Verification filter based on species agreement count
        if verification_filter == "verified":
            media_posts = media_posts.filter(num_identification_agreements__gte=2)
        elif verification_filter == "unverified":
            media_posts = media_posts.filter(num_identification_agreements__lt=2)

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
                "iucn_habitat_lvl1_code": post.iucn_habitat_lvl1.code if post.iucn_habitat_lvl1 else None,
                "iucn_habitat_lvl1_name": post.iucn_habitat_lvl1.name if post.iucn_habitat_lvl1 else None,
                "iucn_habitat_lvl2_code": post.iucn_habitat_lvl2.code if post.iucn_habitat_lvl2 else None,
                "iucn_habitat_lvl2_name": post.iucn_habitat_lvl2.name if post.iucn_habitat_lvl2 else None,
                "iucn_habitat_level_used": (
                    "level2" if post.iucn_habitat_lvl2 else ("level1" if post.iucn_habitat_lvl1 else None)
                ),
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
                "quality_grade": post.quality_grade,
                "num_identification_agreements": post.num_identification_agreements,
                "num_identification_disagreements": post.num_identification_disagreements,
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
            "userId": serializers.UUIDField(required=False, help_text="Filter by user UUID"),
            "userDisplayName": serializers.CharField(
                required=False, help_text="Filter by user display name (case-insensitive contains)"
            ),
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
        user_display_name = data.get("userDisplayName")

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

        if user_display_name:
            media_posts = media_posts.filter(created_by__name__icontains=user_display_name)

        if species is not None:
            media_posts = media_posts.filter(species__name=species)

        # Apply pagination
        paginator = LimitOffsetPagination()
        paginated_media_posts = paginator.paginate_queryset(media_posts, request)

        # Collect and format post information to send.
        # serialize_post handles privacy-aware location selection and normalises
        # legacy integer-code geoprivacy values ("1"/"2"/"3").
        post_data = []
        for post in paginated_media_posts:
            # Skip private sightings – handle both string ("private") and
            # legacy integer code ("3") geoprivacy values.
            if post.geoprivacy in (settings.PRIVACY_SETTING_PRIVATE, "3"):
                continue
            post_data.append(serialize_post(post))

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


class GetClustersByBoundingBoxView(APIView):
    """Return clustered sighting locations for a bounding box + zoom level.

    At low zoom levels (< 13) the response contains cluster features, each with
    ``point_count`` and ``point_count_abbreviated`` properties.  At high zoom (>= 13)
    individual point features are returned instead, with ``id``, ``title``,
    ``species``, ``encounter_date``, and ``geocoded_location`` properties.

    PostGIS ``ST_SnapToGrid`` is used for clustering so the result always reflects
    the current database state with no Python-side caching required.
    Private sightings are always excluded.
    """

    # Zoom level at which we switch from grid clusters → individual points.
    _INDIVIDUAL_ZOOM = 13

    # (min_zoom_inclusive, cell_size_degrees) — first matching entry wins.
    _GRID_SIZES = [
        (11, 0.1),
        (9, 0.3),
        (7, 1.0),
        (5, 2.0),
        (0, 5.0),
    ]

    def _cell_size(self, zoom: int) -> float:
        for threshold, size in self._GRID_SIZES:
            if zoom >= threshold:
                return size
        return 5.0

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        min_lat = data.get("minLatitude")
        max_lat = data.get("maxLatitude")
        min_lng = data.get("minLongitude")
        max_lng = data.get("maxLongitude")
        zoom = int(data.get("zoom", 10))

        if any(v is None for v in [min_lat, max_lat, min_lng, max_lng]):
            return Response(
                {"error": "minLatitude, maxLatitude, minLongitude, maxLongitude are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if zoom >= self._INDIVIDUAL_ZOOM:
            features = self._individual_points(min_lat, max_lat, min_lng, max_lng)
        else:
            features = self._clustered(min_lat, max_lat, min_lng, max_lng, zoom)

        total = sum(f["properties"].get("point_count", 1) for f in features)

        return Response(
            {
                "type": "FeatureCollection",
                "features": features,
                "count": total,
            }
        )

    def _individual_points(self, min_lat, max_lat, min_lng, max_lng):
        from django.contrib.gis.geos import Polygon

        bbox = Polygon.from_bbox((min_lng, min_lat, max_lng, max_lat))
        posts = (
            MediaPost.objects.filter(
                true_location_spatial__isnull=False,
                true_location_spatial__contained=bbox,
            )
            .exclude(geoprivacy__in=[settings.PRIVACY_SETTING_PRIVATE, "3"])
            .select_related("species")[:2000]
        )

        features = []
        for post in posts:
            geoprivacy = _GEOPRIVACY_CODES.get(post.geoprivacy, post.geoprivacy)

            if geoprivacy == settings.PRIVACY_SETTING_PUBLIC:
                if not post.true_location_spatial:
                    continue
                lng = post.true_location_spatial.x
                lat = post.true_location_spatial.y
            elif geoprivacy == settings.PRIVACY_SETTING_OBSCURED:
                if not post.true_location_spatial:
                    continue
                lat, lng = calculate_offset_coordinates(
                    post.true_location_spatial.y,
                    post.true_location_spatial.x,
                    post.obfuscation_range_kilometers,
                )
            else:
                continue

            geocoded_location = ", ".join(filter(None, [post.geocoded_location_locality, post.geocoded_location_state]))

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                    "properties": {
                        "id": str(post.id),
                        "title": post.title or "",
                        "species": getattr(post.species, "name", "") or "",
                        "encounter_date": post.encounter_datetime.isoformat() if post.encounter_datetime else "",
                        "geocoded_location": geocoded_location,
                    },
                }
            )

        return features

    def _clustered(self, min_lat, max_lat, min_lng, max_lng, zoom):
        from django.db import connection

        cell_size = self._cell_size(zoom)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ST_AsGeoJSON(ST_Centroid(ST_Collect(true_location_spatial))),
                    COUNT(*)::int
                FROM socialmedia_mediapost
                WHERE true_location_spatial && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                  AND geoprivacy NOT IN ('private', '3')
                  AND true_location_spatial IS NOT NULL
                GROUP BY ST_SnapToGrid(true_location_spatial, %s)
                """,
                [min_lng, min_lat, max_lng, max_lat, cell_size],
            )
            rows = cursor.fetchall()

        features = []
        for geojson_str, count in rows:
            if not geojson_str:
                continue
            count = int(count)
            abbreviated = f"{count // 1000}k" if count >= 1000 else str(count)
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(geojson_str),
                    "properties": {
                        "point_count": count,
                        "point_count_abbreviated": abbreviated,
                    },
                }
            )

        return features


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
        return Response(serialize_post(post, user=request.user, include_quality_metrics=True))


@extend_schema(
    summary="Vote on a quality metric",
    description="Submit or toggle a quality-metric vote (agree/disagree) for a post. "
    "Voting the same way twice removes the vote (toggle). After each vote the post's "
    "quality_grade is recomputed.",
    request=inline_serializer(
        name="VoteQualityMetricRequest",
        fields={"agree": serializers.BooleanField(help_text="True = agrees with the metric; False = disagrees")},
    ),
    responses={200: None, 400: None, 404: None},
    tags=["Social Media"],
)
class VoteQualityMetricView(APIView):
    """Toggle a quality-metric vote. Restricted to staff and superusers."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, post_id, metric):
        if metric not in PostQualityMetric.METRICS:
            return Response(
                {"error": f"Invalid metric. Valid values: {PostQualityMetric.METRICS}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agree = request.data.get("agree")
        if agree is None:
            return Response({"error": "'agree' field is required (true or false)"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(agree, bool):
            agree = str(agree).lower() == "true"

        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        existing = PostQualityMetric.objects.filter(post=post, user=request.user, metric=metric).first()
        if existing is not None:
            if existing.agree == agree:
                # Same vote again → toggle off
                existing.delete()
            else:
                # Opposite vote → update
                existing.agree = agree
                existing.save(update_fields=["agree"])
        else:
            PostQualityMetric.objects.create(post=post, user=request.user, metric=metric, agree=agree)

        post.recompute_quality_grade()

        return Response(
            {
                "quality_grade": post.quality_grade,
                "num_identification_agreements": post.num_identification_agreements,
                "num_identification_disagreements": post.num_identification_disagreements,
            },
            status=status.HTTP_200_OK,
        )


class UpdateSightingSpeciesView(APIView):
    """Replace the species list for a post. Restricted to staff and superusers.

    Accepts species by common name (Taxon.preferred_common_name) or scientific name
    (Taxon.name). Falls back to legacy SpeciesName lookup for backward compatibility.
    """

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, post_id):
        species_names = [s.strip() for s in (request.data.get("species_list") or []) if s and s.strip()]
        species_names = species_names[: SightingSpecies.MAX_SPECIES]
        update_title = bool(request.data.get("update_title", False))

        if not species_names:
            return Response(
                {"error": "species_list must contain at least one species."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve each name: try Taxon first (common name, then scientific), then SpeciesName
        resolved_taxa = []  # list of Taxon | None
        resolved_species = []  # list of SpeciesName | None
        for name in species_names:
            taxon = (
                Taxon.objects.filter(preferred_common_name__iexact=name).first()
                or Taxon.objects.filter(name__iexact=name).first()
            )
            if taxon:
                resolved_taxa.append(taxon)
                resolved_species.append(None)
            else:
                sp = SpeciesName.objects.filter(name__iexact=name).first()
                if sp:
                    resolved_taxa.append(None)
                    resolved_species.append(sp)
                else:
                    return Response({"error": f"Species not found: {name}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        # Capture the old primary species name before replacing (used for title update)
        if update_title:
            old_taxon = post.taxon
            old_species = post.species
            if old_taxon:
                old_primary_species_name = old_taxon.preferred_common_name or old_taxon.name
            elif old_species:
                old_primary_species_name = old_species.name
            else:
                old_primary_species_name = None

        # Replace all SightingSpecies rows atomically
        SightingSpecies.objects.filter(post=post).delete()
        for rank, (taxon, sp) in enumerate(zip(resolved_taxa, resolved_species), start=1):
            SightingSpecies.objects.create(post=post, species=sp, taxon=taxon, rank=rank)

        # Keep primary FK on MediaPost in sync with rank-1
        primary_taxon = resolved_taxa[0]
        primary_species = resolved_species[0]
        post.taxon = primary_taxon
        post.species = primary_species
        post.save(update_fields=["taxon", "species"])

        # If requested, replace the old primary species name in the post title
        if update_title and old_primary_species_name:
            if primary_taxon:
                new_primary_name = primary_taxon.preferred_common_name or primary_taxon.name
            elif primary_species:
                new_primary_name = primary_species.name
            else:
                new_primary_name = None
            if new_primary_name and old_primary_species_name != new_primary_name:
                updated_title = post.title.replace(old_primary_species_name, new_primary_name, 1)
                if updated_title != post.title:
                    MediaPost.objects.filter(id=post.id).update(title=updated_title)

        result_names = []
        for taxon, sp in zip(resolved_taxa, resolved_species):
            if taxon:
                result_names.append(taxon.preferred_common_name or taxon.name)
            else:
                result_names.append(sp.name)

        return Response({"species_list": result_names}, status=status.HTTP_200_OK)


class UpdateLocationView(APIView):
    """Update latitude, longitude, privacy setting, and obfuscation radius for a post.
    Restricted to staff and superusers."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, post_id):
        try:
            latitude = float(request.data.get("latitude"))
            longitude = float(request.data.get("longitude"))
        except (TypeError, ValueError):
            return Response(
                {"error": "'latitude' and 'longitude' must be valid numbers."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not (-90 <= latitude <= 90):
            return Response({"error": "'latitude' must be between -90 and 90."}, status=status.HTTP_400_BAD_REQUEST)
        if not (-180 <= longitude <= 180):
            return Response({"error": "'longitude' must be between -180 and 180."}, status=status.HTTP_400_BAD_REQUEST)

        privacy_setting = request.data.get("privacy_setting", settings.PRIVACY_SETTING_OBSCURED)
        if privacy_setting not in (
            settings.PRIVACY_SETTING_PUBLIC,
            settings.PRIVACY_SETTING_OBSCURED,
            settings.PRIVACY_SETTING_PRIVATE,
        ):
            return Response({"error": "Invalid 'privacy_setting'."}, status=status.HTTP_400_BAD_REQUEST)

        obfuscation_km = request.data.get("obfuscation_kilometers", 0.5)
        try:
            obfuscation_km = float(obfuscation_km)
        except (TypeError, ValueError):
            return Response(
                {"error": "'obfuscation_kilometers' must be a valid number."}, status=status.HTTP_400_BAD_REQUEST
            )
        if obfuscation_km <= 0:
            return Response(
                {"error": "'obfuscation_kilometers' must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        accuracy_ring_radius_meters = request.data.get("accuracy_ring_radius_meters")
        if accuracy_ring_radius_meters is not None:
            try:
                accuracy_ring_radius_meters = int(accuracy_ring_radius_meters)
            except (TypeError, ValueError):
                return Response(
                    {"error": "'accuracy_ring_radius_meters' must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if accuracy_ring_radius_meters < 0:
                return Response(
                    {"error": "'accuracy_ring_radius_meters' must be 0 or greater."}, status=status.HTTP_400_BAD_REQUEST
                )

        update_kwargs = {
            "true_location_spatial": Point(longitude, latitude, srid=4326),
            "geoprivacy": privacy_setting,
        }

        if privacy_setting == settings.PRIVACY_SETTING_PUBLIC:
            update_kwargs["public_location_latitude"] = latitude
            update_kwargs["public_location_longitude"] = longitude
        elif privacy_setting == settings.PRIVACY_SETTING_OBSCURED:
            update_kwargs["obfuscation_range_kilometers"] = obfuscation_km

        if accuracy_ring_radius_meters is not None:
            update_kwargs["accuracy_ring_radius_meters"] = accuracy_ring_radius_meters

        # Update IUCN habitat classification when location changes
        # ALWAYS populate both Level 1 AND Level 2 habitat codes
        try:
            from siteapps.socialmedia.iucn_habitat_utils import get_iucn_habitat_codes
            from siteapps.socialmedia.models import IUCNHabitatClassification

            habitat_data = get_iucn_habitat_codes(latitude, longitude)
            if habitat_data:
                lvl1_code = habitat_data.get("iucn_habitat_lvl1_code")
                lvl2_code = habitat_data.get("iucn_habitat_lvl2_code")

                # Set FK relationships if classification records exist
                if lvl1_code is not None:
                    try:
                        update_kwargs["iucn_habitat_lvl1"] = IUCNHabitatClassification.objects.get(
                            code=lvl1_code, level="level1"
                        )
                    except IUCNHabitatClassification.DoesNotExist:
                        update_kwargs["iucn_habitat_lvl1"] = None
                        logging.warning(f"No IUCNHabitatClassification found for level1 code {lvl1_code}")
                else:
                    update_kwargs["iucn_habitat_lvl1"] = None

                if lvl2_code is not None:
                    try:
                        update_kwargs["iucn_habitat_lvl2"] = IUCNHabitatClassification.objects.get(
                            code=lvl2_code, level="level2"
                        )
                    except IUCNHabitatClassification.DoesNotExist:
                        update_kwargs["iucn_habitat_lvl2"] = None
                        logging.warning(f"No IUCNHabitatClassification found for level2 code {lvl2_code}")
                else:
                    update_kwargs["iucn_habitat_lvl2"] = None
        except Exception as e:
            logging.error(f"Failed to lookup IUCN habitat classification on location update: {str(e)}")

        for field, value in update_kwargs.items():
            setattr(post, field, value)
        post.save(update_fields=list(update_kwargs.keys()))

        return Response(
            {
                "latitude": latitude,
                "longitude": longitude,
                "privacy_setting": privacy_setting,
                "obfuscation_kilometers": obfuscation_km,
                "accuracy_ring_radius_meters": accuracy_ring_radius_meters,
            },
            status=status.HTTP_200_OK,
        )


class UpdatePostTitleView(APIView):
    """Update the title of a post. Restricted to staff and superusers."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, post_id):
        title = (request.data.get("title") or "").replace("\x00", "").strip()
        if not title:
            return Response({"error": "'title' is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        post.title = title
        post.save(update_fields=["title"])
        return Response({"title": post.title}, status=status.HTTP_200_OK)


class UpdateAnimalCountView(APIView):
    """Update the animal count for a post. Restricted to staff and superusers."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, post_id):
        try:
            count = int(request.data.get("animal_count"))
        except (TypeError, ValueError):
            return Response({"error": "'animal_count' must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        if count < 1:
            return Response({"error": "'animal_count' must be at least 1."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        post.animal_count = count
        post.save(update_fields=["animal_count"])
        return Response({"animal_count": post.animal_count}, status=status.HTTP_200_OK)


class UpdatePostDescriptionView(APIView):
    """Update the text description of a post. Restricted to the post owner."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        description = (request.data.get("description") or "").strip()

        try:
            post = MediaPost.objects.get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        if post.created_by != request.user:
            return Response(
                {"error": "You do not have permission to edit this post."},
                status=status.HTTP_403_FORBIDDEN,
            )

        post.text_content = description
        post.save(update_fields=["text_content"])
        return Response({"description": post.text_content}, status=status.HTTP_200_OK)


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

            # Auto-populate IUCN habitat classification from PostGIS raster data
            # ALWAYS populate both Level 1 AND Level 2 habitat codes
            try:
                from siteapps.socialmedia.iucn_habitat_utils import get_iucn_habitat_codes
                from siteapps.socialmedia.models import IUCNHabitatClassification

                habitat_data = get_iucn_habitat_codes(latitude, longitude)
                if habitat_data:
                    # Store both level 1 and level 2 codes
                    lvl1_code = habitat_data.get("iucn_habitat_lvl1_code")
                    lvl2_code = habitat_data.get("iucn_habitat_lvl2_code")

                    # Set FK relationships if classification records exist
                    if lvl1_code is not None:
                        try:
                            kwargs["iucn_habitat_lvl1"] = IUCNHabitatClassification.objects.get(
                                code=lvl1_code, level="level1"
                            )
                        except IUCNHabitatClassification.DoesNotExist:
                            logging.warning(f"No IUCNHabitatClassification found for level1 code {lvl1_code}")

                    if lvl2_code is not None:
                        try:
                            kwargs["iucn_habitat_lvl2"] = IUCNHabitatClassification.objects.get(
                                code=lvl2_code, level="level2"
                            )
                        except IUCNHabitatClassification.DoesNotExist:
                            logging.warning(f"No IUCNHabitatClassification found for level2 code {lvl2_code}")
            except Exception as e:
                # Log but don't fail the entire request if habitat lookup fails
                logging.error(f"Failed to lookup IUCN habitat classification: {str(e)}")

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
        camera_model = (data.get("cameraModel") or "").replace("\x00", "") or None
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

        # speciesList[0] takes precedence over single 'species' field
        species_names = [s for s in (data.get("speciesList") or []) if s]
        primary_species_name = species_names[0] if species_names else data.get("species")
        if primary_species_name is not None:
            try:
                kwargs["species"] = SpeciesName.objects.get(name=primary_species_name)
            except Exception:
                logging.error(f"No species name found named {primary_species_name}.")

        # Animal count
        animal_count = data.get("animalCount")
        if animal_count is not None:
            try:
                kwargs["animal_count"] = int(animal_count)
            except (ValueError, TypeError):
                pass

        if camera_model is not None:
            kwargs["camera_model"] = camera_model
        if camera_deployment_date is not None:
            kwargs["camera_deployment_date"] = parser.parse(camera_deployment_date)
        if camera_timestamp_offset_error_details is not None:
            kwargs["camera_timestamp_offset_error_details"] = camera_timestamp_offset_error_details
        if habitat_type is not None:
            kwargs["habitat_type"] = habitat_type

        # Sighting type
        sighting_type = data.get("sightingType")
        if sighting_type is not None:
            from siteapps.socialmedia.models import SightingType

            try:
                sighting_type_obj = SightingType.objects.get(code=sighting_type, is_active=True)
                kwargs["sighting_type"] = sighting_type_obj
            except SightingType.DoesNotExist:
                pass

        license_code = data.get("licenseCode")
        attribution_override = data.get("attributionOverride")
        valid_license_codes = {code for code, _ in LICENSE_CHOICES}
        if license_code and license_code in valid_license_codes:
            kwargs["license_code"] = license_code
        if attribution_override is not None:
            kwargs["attribution_override"] = attribution_override

        speciesnet_predictions = data.get("speciesnetPredictions")
        if speciesnet_predictions is not None:
            kwargs["speciesnet_predictions"] = speciesnet_predictions

    @staticmethod
    def validate_and_extract_data(data, request):
        # Extract required data
        encounter_datetime = data.get("encounterDatetime")
        privacy_setting = data.get("privacySetting")
        accuracy_meters = data.get("accuracyMeters")
        geocoded_location_country = data.get("geocodedLocationCountry")
        post_title = (data.get("postTitle") or "").replace("\x00", "") or None

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
            "speciesList": serializers.ListField(
                child=serializers.CharField(),
                required=False,
                help_text="Ordered list of up to 5 species names; first entry is the primary identification",
            ),
            "animalCount": serializers.IntegerField(
                required=False, help_text="Number of individual animals in the sighting"
            ),
            "sightingType": serializers.CharField(
                required=False,
                help_text="Type of sighting: live_sighting, camera_trap, track_sign, killed, or unknown",
            ),
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

        # Apply user's default license if no explicit license was provided in kwargs
        if "license_code" not in kwargs and created_by_user is not None:
            kwargs["license_code"] = created_by_user.default_license

        # Finally, create the post object with given args, ignoring if a duplicate exists
        post, _ = MediaPost.objects.get_or_create(**kwargs, created_by=created_by_user)

        # Auto-populate IUCN habitat classification if coordinates provided
        if "location_latitude" in kwargs and "location_longitude" in kwargs:
            lat = kwargs["location_latitude"]
            lon = kwargs["location_longitude"]

            # Get site configuration to determine which habitat level to use
            site_config = SiteConfiguration.get_instance()
            habitat_level = site_config.habitat_classification_level

            # Query the appropriate IUCN habitat raster
            point_wkt = f"POINT({lon} {lat})"

            with connection.cursor() as cursor:
                if habitat_level == SiteConfiguration.HABITAT_LEVEL_1:
                    # Query level 1 habitat
                    cursor.execute(
                        """
                        SELECT ST_Value(rast, ST_SetSRID(ST_GeomFromText(%s), 4326)) AS habitat_code
                        FROM iucn_habitat_lvl1
                        WHERE ST_Intersects(rast, ST_SetSRID(ST_GeomFromText(%s), 4326))
                        LIMIT 1
                        """,
                        [point_wkt, point_wkt],
                    )
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        habitat_code = int(result[0])
                        # Look up the IUCNHabitatClassification record
                        try:
                            habitat = IUCNHabitatClassification.objects.get(level="level1", code=habitat_code)
                            post.iucn_habitat_lvl1 = habitat
                            post.save(
                                update_fields=[
                                    "iucn_habitat_lvl1",
                                ]
                            )
                        except IUCNHabitatClassification.DoesNotExist:
                            logging.warning(f"No IUCN Level 1 habitat found for code {habitat_code}")

                else:  # HABITAT_LEVEL_2
                    # Query level 2 habitat
                    cursor.execute(
                        """
                        SELECT ST_Value(rast, ST_SetSRID(ST_GeomFromText(%s), 4326)) AS habitat_code
                        FROM iucn_habitat_lvl2
                        WHERE ST_Intersects(rast, ST_SetSRID(ST_GeomFromText(%s), 4326))
                        LIMIT 1
                        """,
                        [point_wkt, point_wkt],
                    )
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        habitat_code = int(result[0])
                        # Look up the IUCNHabitatClassification record
                        try:
                            habitat = IUCNHabitatClassification.objects.get(level="level2", code=habitat_code)
                            post.iucn_habitat_lvl2 = habitat
                            post.save(
                                update_fields=[
                                    "iucn_habitat_lvl2",
                                ]
                            )
                        except IUCNHabitatClassification.DoesNotExist:
                            logging.warning(f"No IUCN Level 2 habitat found for code {habitat_code}")

        # Process multi-species list (up to MAX_SPECIES)
        species_names = [s.strip() for s in (data.get("speciesList") or []) if s and str(s).strip()][
            : SightingSpecies.MAX_SPECIES
        ]
        if species_names:
            # Resolve each name: try Taxon first (common name, then scientific), then SpeciesName
            resolved_taxa = []
            resolved_species = []
            for name in species_names:
                taxon = (
                    Taxon.objects.filter(preferred_common_name__iexact=name).first()
                    or Taxon.objects.filter(name__iexact=name).first()
                )
                if taxon:
                    resolved_taxa.append(taxon)
                    resolved_species.append(None)
                else:
                    sp = SpeciesName.objects.filter(name__iexact=name).first()
                    if sp:
                        resolved_taxa.append(None)
                        resolved_species.append(sp)
                    else:
                        logging.error(f"Species not found when creating SightingSpecies: {name}")
                        continue

            if resolved_taxa or resolved_species:
                post.sighting_species.all().delete()
                for rank, (taxon, sp) in enumerate(zip(resolved_taxa, resolved_species), start=1):
                    SightingSpecies.objects.create(post=post, species=sp, taxon=taxon, rank=rank)
                # Keep primary FK on MediaPost in sync with rank-1
                post.taxon = resolved_taxa[0] if resolved_taxa else None
                post.species = resolved_species[0] if not resolved_taxa or not resolved_taxa[0] else None
                post.save(update_fields=["taxon", "species"])

        # Process multiple media files (mediaList)
        media_list = data.get("mediaList", [])
        if media_list and isinstance(media_list, list):
            # Limit to MAX_MEDIA_PER_SIGHTING
            from siteapps.socialmedia.models import SightingMedia

            media_list = media_list[: SightingMedia.MAX_MEDIA_PER_SIGHTING]

            # Clear existing SightingMedia entries for this post
            SightingMedia.objects.filter(post=post).delete()

            # Process each media file in the list
            for idx, media_item in enumerate(media_list):
                media_bytes_base64 = media_item.get("mediaBytes")
                is_video = media_item.get("isVideo", False)
                display_order = media_item.get("displayOrder", idx + 1)

                if not media_bytes_base64:
                    continue

                try:
                    # Convert and process media
                    media_bytes = convert_base64_bytes(media_bytes_base64, is_video=is_video)
                    content_hash = hashlib.sha256(media_bytes).hexdigest()

                    # Check if Media object already exists
                    media_obj = Media.objects.filter(content_hash=content_hash).first()
                    if not media_obj:
                        # Create new Media object
                        media_obj = create_media(media_bytes, content_hash, request, is_video=is_video)

                    # Link media to post via SightingMedia
                    SightingMedia.objects.create(post=post, media=media_obj, display_order=display_order)

                    # Set the first media as the primary media FK on MediaPost
                    if idx == 0:
                        post.media = media_obj
                        post.save(update_fields=["media"])

                    logging.info(
                        f"Created SightingMedia entry {idx + 1} for post {post.id}, display_order={display_order}"
                    )
                except Exception as e:
                    logging.error(f"Error processing media item {idx + 1}: {e}")
                    # Continue processing other media files even if one fails

        return Response({"status": "success", "post_id": str(post.id)}, status=status.HTTP_201_CREATED)

    def _get_habitat_level1_name(self, code):
        """Map level 1 habitat code to name.

        Based on official IUCN habitat classification scheme codes.
        """
        level1_names = {
            0: "Water",
            100: "Forest",
            200: "Savanna",
            300: "Shrubland",
            400: "Grassland",
            500: "Wetlands (inland)",
            600: "Rocky Areas",
            800: "Desert",
            1400: "Artificial - Terrestrial",
            1700: "Unknown",
        }
        return level1_names.get(code, f"Unknown habitat code ({code})")

    def _get_habitat_level2_name(self, code):
        """Map level 2 habitat code to name.

        Based on official IUCN habitat classification scheme codes.
        """
        level2_names = {
            0: "Water",
            100: "Forest",
            101: "Forest - Boreal",
            102: "Forest - Subarctic",
            103: "Forest - Subantarctic",
            104: "Forest - Temperate",
            105: "Forest - Subtropical-tropical dry",
            106: "Forest - Subtropical-tropical moist lowland",
            107: "Forest - Subtropical-tropical mangrove vegetation",
            108: "Forest - Subtropical-tropical swamp",
            109: "Forest - Subtropical-tropical moist montane",
            200: "Savanna",
            201: "Savanna - Dry",
            202: "Savanna - Moist",
            300: "Shrubland",
            301: "Shrubland - Subarctic",
            302: "Shrubland - Subantarctic",
            303: "Shrubland - Boreal",
            304: "Shrubland - Temperate",
            305: "Shrubland - Subtropical-tropical dry",
            306: "Shrubland - Subtropical-tropical moist",
            307: "Shrubland - Subtropical-tropical high altitude",
            308: "Shrubland - Mediterranean-type",
            400: "Grassland",
            401: "Grassland - Tundra",
            402: "Grassland - Subarctic",
            403: "Grassland - Subantarctic",
            404: "Grassland - Temperate",
            405: "Grassland - Subtropical-tropical dry",
            406: "Grassland - Subtropical-tropical seasonally wet or flooded",
            407: "Grassland - Subtropical-tropical high altitude",
            500: "Wetlands (inland)",
            501: "Wetlands (inland) - Permanent rivers streams creeks",
            502: "Wetlands (inland) - Seasonal/intermittent/irregular rivers/streams/creeks",
            503: "Wetlands (inland) - Shrub dominated wetlands",
            504: "Wetlands (inland) - Bogs/marshes/swamps/fens/peatlands",
            505: "Wetlands (inland) - Permanent freshwater lakes",
            506: "Wetlands (inland) - Seasonal/intermittent freshwater lakes (over 8 ha)",
            507: "Wetlands (inland) - Permanent freshwater marshes/pools (under 8 ha)",
            508: "Wetlands (inland) - Seasonal/intermittent freshwater marshes/pools (under 8 ha)",
            509: "Wetlands (inland) - Freshwater springs and oases",
            510: "Wetlands (inland) - Tundra wetlands",
            511: "Wetlands (inland) - Alpine wetlands",
            512: "Wetlands (inland) - Geothermal wetlands",
            513: "Wetlands (inland) - Permanent inland deltas",
            514: "Wetlands (inland) - Permanent saline brackish or alkaline lakes",
            515: "Wetlands (inland) - Seasonal/intermittent saline brackish or alkaline lakes and flats",
            516: "Wetlands (inland) - Permanent /saline / brackish or alkaline marshes/pools",
            517: "Wetlands (inland) - Seasonal/intermittent /saline / brackish or alkaline marshes/pools",
            518: "Wetlands (inland) / Karst and other subterranean hydrological systems",
            600: "Rocky Areas",
            800: "Desert",
            801: "Desert - Hot",
            802: "Desert - Temperate",
            803: "Desert - Cold",
            1400: "Artificial - Terrestrial",
            1401: "Arable land",
            1402: "Pastureland",
            1403: "Plantations",
            1404: "Rural Gardens",
            1405: "Urban Areas",
            1406: "Subtropical/Tropical Heavily Degraded Former Forest",
            1700: "Unknown",
        }
        return level2_names.get(code, f"Unknown habitat code ({code})")


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


# ==========================================
# Sighting Type Endpoints
# ==========================================


class ListSightingTypesView(APIView):
    """List all active sighting types for dropdown selection."""

    authentication_classes = []
    permission_classes = []  # Public endpoint

    def get(self, request):
        from siteapps.socialmedia.models import SightingType

        types = SightingType.objects.filter(is_active=True).order_by("display_order", "display_name")
        data = [
            {
                "id": str(stype.id),
                "code": stype.code,
                "displayName": stype.display_name,
                "description": stype.description,
            }
            for stype in types
        ]
        return Response(data, status=status.HTTP_200_OK)


class GetSiteConfigurationView(APIView):
    """Get site-wide configuration settings."""

    authentication_classes = []
    permission_classes = []  # Public endpoint

    def get(self, request):
        from siteapps.socialmedia.models import SiteConfiguration

        config = SiteConfiguration.load()
        data = {
            "maxSightingImages": config.max_sighting_images,
        }
        return Response(data, status=status.HTTP_200_OK)


# ==========================================
# User Sighting Location CRUD Endpoints
# ==========================================


@extend_schema(
    summary="List user's saved sighting locations",
    description="Retrieve all saved sighting locations for the authenticated user.",
    responses={200: None, 401: None},
    tags=["User Locations"],
)
class ListUserLocationsView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        locations = UserSightingLocation.objects.filter(user=request.user).order_by("name")
        data = [
            {
                "id": str(loc.id),
                "name": loc.name,
                "description": loc.description,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "created": loc.created.isoformat(),
                "camera_model": loc.camera_model,
                "camera_serial_number": loc.camera_serial_number,
                "camera_deployment_date": loc.camera_deployment_date,
                "camera_timestamp_offset_error_details": loc.camera_timestamp_offset_error_details,
            }
            for loc in locations
        ]
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Create a new sighting location",
    description="Save a new named location for quick sighting submission.",
    request=inline_serializer(
        name="CreateLocationRequest",
        fields={
            "name": serializers.CharField(help_text="Location name (e.g., 'Backyard')"),
            "description": serializers.CharField(required=False, help_text="Optional description"),
            "latitude": serializers.FloatField(),
            "longitude": serializers.FloatField(),
        },
    ),
    responses={201: None, 400: None, 401: None},
    tags=["User Locations"],
)
class CreateUserLocationView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if not name:
            return Response({"error": "Location name is required."}, status=status.HTTP_400_BAD_REQUEST)

        if latitude is None or longitude is None:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return Response({"error": "Invalid latitude or longitude."}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return Response({"error": "Latitude or longitude out of valid range."}, status=status.HTTP_400_BAD_REQUEST)

        camera_model = (data.get("camera_model") or "").strip() or None
        camera_serial_number = (data.get("camera_serial_number") or "").strip() or None
        camera_deployment_date = (data.get("camera_deployment_date") or "").strip() or None
        camera_timestamp_offset_error_details = (
            data.get("camera_timestamp_offset_error_details") or ""
        ).strip() or None

        location = UserSightingLocation.objects.create(
            user=request.user,
            name=name,
            description=description,
            latitude=latitude,
            longitude=longitude,
            camera_model=camera_model,
            camera_serial_number=camera_serial_number,
            camera_deployment_date=camera_deployment_date,
            camera_timestamp_offset_error_details=camera_timestamp_offset_error_details,
        )

        return Response(
            {
                "id": str(location.id),
                "name": location.name,
                "description": location.description,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "camera_model": location.camera_model,
                "camera_serial_number": location.camera_serial_number,
                "camera_deployment_date": location.camera_deployment_date,
                "camera_timestamp_offset_error_details": location.camera_timestamp_offset_error_details,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Update a sighting location",
    description="Update an existing saved location.",
    request=inline_serializer(
        name="UpdateLocationRequest",
        fields={
            "name": serializers.CharField(required=False),
            "description": serializers.CharField(required=False),
            "latitude": serializers.FloatField(required=False),
            "longitude": serializers.FloatField(required=False),
        },
    ),
    responses={200: None, 400: None, 401: None, 403: None, 404: None},
    tags=["User Locations"],
)
class UpdateUserLocationView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, location_id):
        try:
            location = UserSightingLocation.objects.get(id=location_id)
        except UserSightingLocation.DoesNotExist:
            return Response({"error": "Location not found."}, status=status.HTTP_404_NOT_FOUND)

        if location.user != request.user:
            return Response(
                {"error": "You do not have permission to edit this location."}, status=status.HTTP_403_FORBIDDEN
            )

        data = request.data

        if "name" in data:
            location.name = (data["name"] or "").strip()
        if "description" in data:
            location.description = (data["description"] or "").strip()
        if "latitude" in data:
            try:
                location.latitude = float(data["latitude"])
            except (ValueError, TypeError):
                return Response({"error": "Invalid latitude."}, status=status.HTTP_400_BAD_REQUEST)
        if "longitude" in data:
            try:
                location.longitude = float(data["longitude"])
            except (ValueError, TypeError):
                return Response({"error": "Invalid longitude."}, status=status.HTTP_400_BAD_REQUEST)
        if "camera_model" in data:
            location.camera_model = (data["camera_model"] or "").strip() or None
        if "camera_serial_number" in data:
            location.camera_serial_number = (data["camera_serial_number"] or "").strip() or None
        if "camera_deployment_date" in data:
            location.camera_deployment_date = (data["camera_deployment_date"] or "").strip() or None
        if "camera_timestamp_offset_error_details" in data:
            location.camera_timestamp_offset_error_details = (
                data["camera_timestamp_offset_error_details"] or ""
            ).strip() or None

        location.save()

        return Response(
            {
                "id": str(location.id),
                "name": location.name,
                "description": location.description,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "camera_model": location.camera_model,
                "camera_serial_number": location.camera_serial_number,
                "camera_deployment_date": location.camera_deployment_date,
                "camera_timestamp_offset_error_details": location.camera_timestamp_offset_error_details,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Delete a sighting location",
    description="Delete a saved sighting location.",
    responses={204: None, 401: None, 403: None, 404: None},
    tags=["User Locations"],
)
class DeleteUserLocationView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, location_id):
        try:
            location = UserSightingLocation.objects.get(id=location_id)
        except UserSightingLocation.DoesNotExist:
            return Response({"error": "Location not found."}, status=status.HTTP_404_NOT_FOUND)

        if location.user != request.user:
            return Response(
                {"error": "You do not have permission to delete this location."}, status=status.HTTP_403_FORBIDDEN
            )

        location.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==========================================
# Bulk Upload Session Endpoints
# ==========================================


class BulkUploadSessionCreateView(APIView):
    """Create a new bulk upload session."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from siteapps.socialmedia.models import BulkUploadSession

        name = (request.data.get("name") or "Bulk Upload").strip()
        image_count = int(request.data.get("image_count", 0))
        session = BulkUploadSession.objects.create(
            user=request.user,
            name=name,
            image_count=image_count,
        )
        return Response(
            {"id": str(session.id), "name": session.name, "image_count": session.image_count},
            status=status.HTTP_201_CREATED,
        )


class BulkUploadSessionListView(APIView):
    """List the current user's bulk upload sessions, newest first."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from siteapps.socialmedia.models import BulkUploadSession

        sessions = BulkUploadSession.objects.filter(user=request.user).order_by("-created")
        data = [
            {
                "id": str(s.id),
                "name": s.name,
                "image_count": s.image_count,
                "post_count": len(s.post_ids),
                "created": s.created.isoformat(),
            }
            for s in sessions
        ]
        return Response(data, status=status.HTTP_200_OK)


class BulkUploadSessionDetailView(APIView):
    """Return a single bulk upload session including post_ids and gpx_track."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        from siteapps.socialmedia.models import BulkUploadSession

        try:
            session = BulkUploadSession.objects.get(id=session_id, user=request.user)
        except BulkUploadSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize gpx_track as [[lng, lat], ...] for GeoJSON / MapLibre consumption
        gpx_coords = []
        if session.gpx_track:
            gpx_coords = list(session.gpx_track.coords)  # LineString.coords → ((lng, lat), ...)

        return Response(
            {
                "id": str(session.id),
                "name": session.name,
                "image_count": session.image_count,
                "post_ids": session.post_ids,
                "gpx_track": gpx_coords,
                "created": session.created.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, session_id):
        from siteapps.socialmedia.models import BulkUploadSession

        try:
            session = BulkUploadSession.objects.get(id=session_id, user=request.user)
        except BulkUploadSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        new_name = request.data.get("name", "").strip()
        if not new_name:
            return Response({"error": "name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_name) > 255:
            return Response({"error": "name must be 255 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)

        session.name = new_name
        session.save(update_fields=["name"])
        return Response({"id": str(session.id), "name": session.name}, status=status.HTTP_200_OK)


class BulkUploadSessionAddPostView(APIView):
    """Append a MediaPost UUID to a bulk upload session's post_ids list."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from siteapps.socialmedia.models import BulkUploadSession

        try:
            session = BulkUploadSession.objects.get(id=session_id, user=request.user)
        except BulkUploadSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        post_id = request.data.get("post_id")
        if not post_id:
            return Response({"error": "post_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        post_id_str = str(post_id)
        if post_id_str not in session.post_ids:
            session.post_ids.append(post_id_str)
            session.save(update_fields=["post_ids"])

        return Response({"post_ids": session.post_ids}, status=status.HTTP_200_OK)


class BulkUploadSessionGPXView(APIView):
    """Accept a multipart GPX file upload, parse to PostGIS LineString, and store on the session."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        import re as _re
        import xml.etree.ElementTree as ET

        from django.contrib.gis.geos import LineString

        from siteapps.socialmedia.models import BulkUploadSession

        try:
            session = BulkUploadSession.objects.get(id=session_id, user=request.user)
        except BulkUploadSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        gpx_file = request.FILES.get("gpx_file")
        if not gpx_file:
            return Response({"error": "gpx_file is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tree = ET.parse(gpx_file)
            root = tree.getroot()
            ns_match = _re.match(r"\{[^}]*\}", root.tag)
            ns = ns_match.group(0) if ns_match else ""
            coords = []
            for trkpt in root.iter(f"{ns}trkpt"):
                coords.append((float(trkpt.get("lon")), float(trkpt.get("lat"))))
        except Exception as e:
            return Response({"error": f"Failed to parse GPX file: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        if len(coords) < 2:
            return Response(
                {"error": "GPX file must contain at least 2 track points."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.gpx_track = LineString(coords, srid=4326)
        session.save(update_fields=["gpx_track"])

        return Response({"point_count": len(coords)}, status=status.HTTP_200_OK)
