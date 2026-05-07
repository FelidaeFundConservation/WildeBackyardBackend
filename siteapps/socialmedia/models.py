import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from siteapps.license_constants import DEFAULT_LICENSE, LICENSE_CHOICES
from siteapps.species.models import SpeciesName, Taxon

User = get_user_model()


class SightingType(TimeStampedModel):
    """Types of wildlife sightings (e.g., live sighting, camera trap, track/sign).

    Allows admins to manage available sighting types via Django admin.
    Uses integer primary key for simplicity and performance.
    """

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True, help_text="Unique code identifier (e.g., 'live_sighting')")
    display_name = models.CharField(max_length=100, help_text="Display name (e.g., 'Live Sighting')")
    description = models.TextField(blank=True, help_text="Optional description of this sighting type")
    display_order = models.PositiveSmallIntegerField(default=100, help_text="Order for display in dropdowns")
    is_active = models.BooleanField(default=True, help_text="Whether this type is available for selection")

    class Meta:
        ordering = ["display_order", "display_name"]
        verbose_name = "Sighting Type"
        verbose_name_plural = "Sighting Types"

    def __str__(self):
        return self.display_name


class SiteConfiguration(TimeStampedModel):
    """Site-wide configuration settings.

    Singleton model - only one instance should exist.
    Allows admins to configure various site parameters via Django admin.
    """

    HABITAT_LEVEL_1 = "level1"
    HABITAT_LEVEL_2 = "level2"

    HABITAT_LEVEL_CHOICES = [
        (HABITAT_LEVEL_1, "Level 1 (Broad classification)"),
        (HABITAT_LEVEL_2, "Level 2 (Detailed classification)"),
    ]

    id = models.AutoField(primary_key=True)
    max_sighting_images = models.PositiveSmallIntegerField(
        default=5, help_text="Maximum number of images that can be attached to a single sighting"
    )

    habitat_classification_level = models.CharField(
        max_length=10,
        choices=HABITAT_LEVEL_CHOICES,
        default=HABITAT_LEVEL_1,
        help_text="Which IUCN habitat classification level to use for automatic habitat lookup",
    )

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the configuration."""
        pass

    @classmethod
    def load(cls):
        """Load the singleton instance, creating it if necessary."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_instance(cls):
        """Alias for load() - get the singleton instance."""
        return cls.load()

    def __str__(self):
        return "Site Configuration"


class IUCNHabitatClassification(models.Model):
    """IUCN habitat classification lookup table.

    Stores the official IUCN habitat codes and their corresponding names
    for both Level 1 (broad) and Level 2 (detailed) classifications.
    """

    LEVEL_1 = "level1"
    LEVEL_2 = "level2"

    LEVEL_CHOICES = [
        (LEVEL_1, "Level 1"),
        (LEVEL_2, "Level 2"),
    ]

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, help_text="Classification level (broad or detailed)")
    code = models.IntegerField(help_text="IUCN numeric habitat code (e.g., 100=Forest, 400=Grassland)")
    name = models.CharField(max_length=128, help_text="Human-readable habitat name")
    description = models.TextField(blank=True, help_text="Optional detailed description of this habitat type")

    class Meta:
        verbose_name = "IUCN Habitat Classification"
        verbose_name_plural = "IUCN Habitat Classifications"
        unique_together = [["level", "code"]]
        ordering = ["level", "code"]
        indexes = [
            models.Index(fields=["level", "code"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_level_display()}, code={self.code})"


# Images or videos
class Media(TimeStampedModel):
    # UUID for the image
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Assuming all media is either images or videos, so using a boolean field
    is_video = models.BooleanField(default=False)

    # The path to the media file in storage
    file_cloud_path = models.CharField(max_length=250)

    # Unique content identifier for deduplication
    content_hash = models.CharField(max_length=64)

    # The user who uploaded the media
    uploaded_by = models.ForeignKey(User, related_name="uploaded_by_user", on_delete=models.SET_NULL, null=True)


# Base post class, used for replies to posts
class TextComment(TimeStampedModel):
    # UUID for the post
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The user who posted the comment
    created_by = models.ForeignKey(User, related_name="created_by_user", on_delete=models.SET_NULL, null=True)

    # The text content of the comment
    text_content = models.TextField(max_length=4000, null=True)

    # Like count
    upvoted_by = models.ManyToManyField(User, blank=True, related_name="upvoted_by")


# A specialized post with media and title, used for main posts
class MediaPost(TextComment):
    # Relative second-level comments in reply to this post
    replies = models.ManyToManyField(TextComment, related_name="post_replies", blank=True)

    # Title of the post
    title = models.TextField(max_length=80)

    # The media the comment contains, if any
    media = models.ForeignKey(Media, related_name="post_media", on_delete=models.SET_NULL, null=True)

    # Circle radius where the true point may be within
    accuracy_ring_radius_meters = models.IntegerField(null=True)

    # When the encounter occurred
    encounter_datetime = models.DateTimeField()

    # All media types are collapsed into a single model for query performance,
    # Field names are differentiated for security (i.e public latitude, private latitude, etc.)
    geoprivacy = models.CharField(
        choices=(
            (1, settings.PRIVACY_SETTING_PUBLIC),
            (2, settings.PRIVACY_SETTING_OBSCURED),
            (3, settings.PRIVACY_SETTING_PRIVATE),
        ),
        max_length=16,
    )

    # The species the user specified was sighted
    species = models.ForeignKey(SpeciesName, on_delete=models.SET_NULL, null=True, blank=True)
    # iNaturalist-derived taxon FK — preferred over species FK for new sightings
    taxon = models.ForeignKey(Taxon, on_delete=models.SET_NULL, null=True, blank=True, related_name="media_posts")

    ########################
    # Public Information
    ########################
    # The location of the post, only used if public location is given.
    public_location_latitude = models.FloatField(null=True)
    public_location_longitude = models.FloatField(null=True)

    # Length of one side of the obfuscation box
    obfuscation_range_kilometers = models.FloatField(null=True)

    # Human readable location info
    geocoded_location_locality = models.CharField(max_length=64, null=True)
    geocoded_location_state = models.CharField(max_length=64, null=True)
    geocoded_location_country = models.CharField(max_length=64, null=True)
    geocoded_location_zip_code = models.CharField(max_length=64, null=True)

    # Supplementary info to understand the submission
    camera_model = models.CharField(max_length=64, null=True)
    camera_deployment_date = models.CharField(max_length=32, null=True)
    camera_timestamp_offset_error_details = models.CharField(max_length=512, null=True)

    habitat_type = models.CharField(max_length=64, null=True)

    ##############################
    # IUCN Habitat Classification
    ##############################
    # Automatically populated from IUCN habitat raster data based on sighting location
    iucn_habitat_lvl1 = models.ForeignKey(
        "IUCNHabitatClassification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_posts_lvl1",
        limit_choices_to={"level": "level1"},
        help_text="Level 1 IUCN habitat classification (broad categories)",
    )
    iucn_habitat_lvl2 = models.ForeignKey(
        "IUCNHabitatClassification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_posts_lvl2",
        limit_choices_to={"level": "level2"},
        help_text="Level 2 IUCN habitat classification (detailed categories)",
    )

    ##############################
    # Identification Quality Fields
    ##############################
    QUALITY_GRADE_CASUAL = "casual"
    QUALITY_GRADE_NEEDS_ID = "needs_id"
    QUALITY_GRADE_RESEARCH = "research"
    QUALITY_GRADE_CHOICES = [
        (QUALITY_GRADE_CASUAL, "Casual"),
        (QUALITY_GRADE_NEEDS_ID, "Needs ID"),
        (QUALITY_GRADE_RESEARCH, "Research"),
    ]

    # Number of identifications that agree with the community taxon
    num_identification_agreements = models.IntegerField(default=0)

    # Number of identifications that disagree with the community taxon
    num_identification_disagreements = models.IntegerField(default=0)

    # Overall data quality grade for this sighting
    quality_grade = models.CharField(
        max_length=16,
        choices=QUALITY_GRADE_CHOICES,
        default=QUALITY_GRADE_CASUAL,
    )

    ##############################
    # Observation Counts
    ##############################
    # Number of individual animals visible in the sighting
    animal_count = models.PositiveSmallIntegerField(default=1, help_text="Number of individual animals in the sighting")

    ##############################
    # Sighting Type
    ##############################
    # Foreign key to SightingType model for admin-manageable sighting types
    sighting_type = models.ForeignKey(
        SightingType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        help_text="Type of sighting (live, camera trap, track/sign, etc.)",
    )

    ##############################
    # Licensing and Attribution
    ##############################
    # The license under which this sighting's media and data are released
    license_code = models.CharField(
        max_length=32,
        choices=LICENSE_CHOICES,
        default=DEFAULT_LICENSE,
        help_text="License for media and sighting data",
    )
    # Optional attribution text; if blank the poster's display name is used
    attribution_override = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Custom attribution name; leave blank to use poster's display name",
    )

    ##############################
    # PostGIS Spatial Fields
    ##############################
    # Spatial point field for true location (uses SRID 4326 - WGS84)
    # Automatically indexed by PostGIS
    # THIS IS THE CANONICAL SOURCE FOR ALL LOCATION DATA
    # Privacy transformations are applied during data retrieval, not storage
    true_location_spatial = gis_models.PointField(srid=4326, null=True, blank=True, spatial_index=True)

    ##############################
    # ML Prediction Data
    ##############################
    # SpeciesNet prediction payload for the sighting image (populated during bulk upload)
    speciesnet_predictions = models.JSONField(
        null=True,
        blank=True,
        help_text="SpeciesNet ML prediction payload for the sighting image",
    )

    class Meta:
        indexes = [
            GinIndex(fields=["speciesnet_predictions"], name="mediapost_speciesnet_gin"),
        ]

    def recompute_quality_grade(self):
        """Recompute quality_grade, num_identification_agreements, and
        num_identification_disagreements from current votes and save the post.

        Grade logic (modelled on iNaturalist):
        - casual  : missing encounter_datetime, location, or media evidence;
                    OR majority of "wild" votes disagree.
        - research: all basics present + has species + ID agreements > disagreements
                    with at least 2 agreeing votes.
        - needs_id: all basics present but species/ID threshold not yet met.
        """
        # Denormalise species-identification vote counts
        id_votes = self.quality_metrics.filter(metric=PostQualityMetric.SPECIES_ID)
        self.num_identification_agreements = id_votes.filter(agree=True).count()
        self.num_identification_disagreements = id_votes.filter(agree=False).count()

        # --- Casual checks (any failure → casual) ---
        has_date = self.encounter_datetime is not None
        has_location = self.true_location_spatial is not None or (
            self.public_location_latitude is not None and self.public_location_longitude is not None
        )
        has_evidence = self.media is not None

        if not (has_date and has_location and has_evidence):
            self.quality_grade = self.QUALITY_GRADE_CASUAL
            self.save(
                update_fields=["quality_grade", "num_identification_agreements", "num_identification_disagreements"]
            )
            return

        wild_votes = self.quality_metrics.filter(metric=PostQualityMetric.WILD)
        if wild_votes.exists():
            not_wild = wild_votes.filter(agree=False).count()
            is_wild = wild_votes.filter(agree=True).count()
            if not_wild > is_wild:
                self.quality_grade = self.QUALITY_GRADE_CASUAL
                self.save(
                    update_fields=["quality_grade", "num_identification_agreements", "num_identification_disagreements"]
                )
                return

        # --- Research check ---
        if (
            self.species is not None
            and self.num_identification_agreements >= 2
            and self.num_identification_agreements > self.num_identification_disagreements
        ):
            self.quality_grade = self.QUALITY_GRADE_RESEARCH
        else:
            self.quality_grade = self.QUALITY_GRADE_NEEDS_ID

        self.save(update_fields=["quality_grade", "num_identification_agreements", "num_identification_disagreements"])


class PostQualityMetric(TimeStampedModel):
    """Records a single user's vote on a quality dimension for a MediaPost.

    Modelled on iNaturalist's QualityMetric system. Each (post, user, metric)
    combination is unique — voting again on the same metric toggles the value.
    """

    WILD = "wild"
    LOCATION = "location"
    DATE = "date"
    EVIDENCE = "evidence"
    SPECIES_ID = "species_id"

    METRIC_CHOICES = [
        (WILD, "Is the organism wild?"),
        (LOCATION, "Does the location seem accurate?"),
        (DATE, "Does the date seem accurate?"),
        (EVIDENCE, "Is there sufficient evidence of the organism?"),
        (SPECIES_ID, "Does this match the identified species?"),
    ]
    METRICS = [m[0] for m in METRIC_CHOICES]

    METRIC_QUESTIONS = {
        WILD: "Is the organism wild?",
        LOCATION: "Does the location seem accurate?",
        DATE: "Does the date seem accurate?",
        EVIDENCE: "Is there sufficient evidence of the organism?",
        SPECIES_ID: "Does this match the identified species?",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    post = models.ForeignKey(MediaPost, related_name="quality_metrics", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="quality_metric_votes", on_delete=models.CASCADE)

    metric = models.CharField(max_length=16, choices=METRIC_CHOICES)

    # True = agrees with the metric (e.g. "yes, it is wild"); False = disagrees
    agree = models.BooleanField(default=True)

    class Meta:
        unique_together = [("post", "user", "metric")]


class SightingSpecies(TimeStampedModel):
    """Records one of up to MAX_SPECIES species associated with a MediaPost.

    rank=1 is the primary identification (mirrors MediaPost.species FK).
    rank 2-5 are additional species observed in the same sighting.
    """

    MAX_SPECIES = 5

    post = models.ForeignKey(MediaPost, related_name="sighting_species", on_delete=models.CASCADE)
    species = models.ForeignKey(SpeciesName, on_delete=models.CASCADE, null=True, blank=True)
    # iNaturalist-derived taxon FK — preferred for new sightings
    taxon = models.ForeignKey(Taxon, on_delete=models.SET_NULL, null=True, blank=True, related_name="sighting_species")

    # 1 = primary identification, 2-5 = additional
    rank = models.PositiveSmallIntegerField(default=1)

    class Meta:
        # ("post", "taxon") uniqueness is enforced only when taxon is set
        unique_together = [("post", "rank")]
        ordering = ["rank"]


class SightingMedia(TimeStampedModel):
    """Links multiple media files (up to 5) to a single sighting/post.

    This allows users to attach multiple photos/videos to one sighting.
    The MediaPost.media FK is kept for backwards compatibility and represents
    the primary/first media item.
    """

    MAX_MEDIA_PER_SIGHTING = 5

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    post = models.ForeignKey(MediaPost, related_name="additional_media", on_delete=models.CASCADE)
    media = models.ForeignKey(Media, on_delete=models.CASCADE)

    # Order of media within the sighting (1 = primary, 2-5 = additional)
    display_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [("post", "media")]
        ordering = ["display_order"]


class UserSightingLocation(TimeStampedModel):
    """User-defined named locations for quick sighting submission.

    Allows users to save frequently used locations (e.g., "Backyard", "Front Trail")
    for reuse when creating sightings.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, related_name="sighting_locations", on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="Name for this location (e.g., 'Backyard', 'North Trail')")
    description = models.TextField(max_length=500, blank=True, help_text="Optional description of the location")

    latitude = models.FloatField()
    longitude = models.FloatField()

    # Optional: use PostGIS for spatial indexing
    location_spatial = gis_models.PointField(srid=4326, null=True, blank=True, spatial_index=True)

    # Camera trap fields (optional — only relevant for camera trap deployments)
    camera_model = models.CharField(max_length=64, null=True, blank=True)
    camera_serial_number = models.CharField(max_length=64, null=True, blank=True)
    camera_deployment_date = models.CharField(max_length=32, null=True, blank=True)
    camera_timestamp_offset_error_details = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["user", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"

    def save(self, *args, **kwargs):
        # Automatically populate spatial field from lat/lng
        if self.latitude and self.longitude:
            from django.contrib.gis.geos import Point

            self.location_spatial = Point(self.longitude, self.latitude, srid=4326)
        super().save(*args, **kwargs)


# Model to handle reports for inappropriate content
class InappropriateContentReport(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who reported the media/comment
    reported_by = models.ForeignKey(User, related_name="reported_by_user", on_delete=models.SET_NULL, null=True)

    # The user the report was made against
    reported_user = models.ForeignKey(User, related_name="reported_user", on_delete=models.SET_NULL, null=True)

    # Can report either comments or posts
    reported_comment = models.ForeignKey(
        TextComment, related_name="reported_comment", on_delete=models.SET_NULL, null=True, blank=True
    )
    reported_post = models.ForeignKey(
        MediaPost, related_name="reported_post", on_delete=models.SET_NULL, null=True, blank=True
    )

    # Whether the report has been handled by a moderator/staff
    resolved = models.BooleanField(default=False)

    # Describes the offense the user was warned for (if any)
    warning_notes = models.CharField(max_length=800, default="")


class BulkUploadSession(TimeStampedModel):
    """Tracks a user's bulk upload walk session, including optional GPX track.

    Created by the web frontend at the start of a bulk upload.  Post IDs are
    appended as each sighting is submitted.  An optional GPX track (LineString)
    is stored in PostGIS for spatial queries and map display.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bulk_upload_sessions")
    name = models.CharField(max_length=255)
    image_count = models.PositiveIntegerField(default=0)

    # Post UUIDs submitted as part of this session
    post_ids = models.JSONField(default=list, blank=True)

    # Parsed GPX walk track stored as a PostGIS LineString (SRID 4326)
    gpx_track = gis_models.LineStringField(srid=4326, null=True, blank=True, spatial_index=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.name} ({self.image_count} images) — {self.created:%Y-%m-%d %H:%M}"
