import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from siteapps.license_constants import DEFAULT_LICENSE, LICENSE_CHOICES
from siteapps.species.models import SpeciesName, Taxon

User = get_user_model()


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
