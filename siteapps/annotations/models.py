import uuid

from django.db import models
from model_utils.models import TimeStampedModel

from siteapps.socialmedia.models import Media


# MegaDetector category labels
MEGADETECTOR_CATEGORY_ANIMAL = "animal"
MEGADETECTOR_CATEGORY_PERSON = "person"
MEGADETECTOR_CATEGORY_VEHICLE = "vehicle"

MEGADETECTOR_CATEGORY_CHOICES = (
    (MEGADETECTOR_CATEGORY_ANIMAL, "Animal"),
    (MEGADETECTOR_CATEGORY_PERSON, "Person"),
    (MEGADETECTOR_CATEGORY_VEHICLE, "Vehicle"),
)


class MegaDetectorAnnotation(TimeStampedModel):
    """Stores per-image MegaDetector detection results for a Media object."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The image that was processed
    media = models.ForeignKey(
        Media,
        related_name="megadetector_annotations",
        on_delete=models.CASCADE,
    )

    # MegaDetector model version that produced this result, e.g. "MDv5a"
    model_version = models.CharField(max_length=64)

    # Highest confidence across all detections in this image (null if no detections)
    max_detection_conf = models.FloatField(null=True, blank=True)

    # Full raw JSON response from MegaDetector for reference / reprocessing
    raw_result = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"MegaDetectorAnnotation({self.media_id}, {self.model_version})"


class MegaDetectorBoundingBox(TimeStampedModel):
    """A single detection bounding box returned by MegaDetector."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    annotation = models.ForeignKey(
        MegaDetectorAnnotation,
        related_name="bounding_boxes",
        on_delete=models.CASCADE,
    )

    # Detection category: animal / person / vehicle
    category = models.CharField(
        max_length=16,
        choices=MEGADETECTOR_CATEGORY_CHOICES,
    )

    # Detection confidence score (0–1)
    confidence = models.FloatField()

    # Bounding box coordinates — all normalised to [0, 1] relative to image dimensions
    # Following MegaDetector convention: (x_min, y_min, width, height)
    bbox_x = models.FloatField()
    bbox_y = models.FloatField()
    bbox_width = models.FloatField()
    bbox_height = models.FloatField()

    class Meta:
        ordering = ["-confidence"]

    def __str__(self):
        return f"BoundingBox({self.category}, conf={self.confidence:.2f})"


class SpeciesNetAnnotation(TimeStampedModel):
    """Stores per-image (or per-crop) SpeciesNet classification results."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The source image
    media = models.ForeignKey(
        Media,
        related_name="speciesnet_annotations",
        on_delete=models.CASCADE,
    )

    # Optional link to the bounding box crop that SpeciesNet was run on.
    # Null means SpeciesNet was run on the full image.
    megadetector_bbox = models.ForeignKey(
        MegaDetectorBoundingBox,
        related_name="speciesnet_annotations",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # SpeciesNet model version that produced this result, e.g. "v4.0.1"
    model_version = models.CharField(max_length=64)

    # Full raw JSON response from SpeciesNet
    raw_result = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"SpeciesNetAnnotation({self.media_id}, {self.model_version})"


class SpeciesNetPrediction(TimeStampedModel):
    """A single ranked species prediction produced by SpeciesNet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    annotation = models.ForeignKey(
        SpeciesNetAnnotation,
        related_name="predictions",
        on_delete=models.CASCADE,
    )

    # Predicted taxon — scientific name as returned by SpeciesNet
    scientific_name = models.CharField(max_length=200)

    # Human-readable common name (may be empty if not provided)
    common_name = models.CharField(max_length=200, blank=True, default="")

    # Classification confidence score (0–1)
    confidence = models.FloatField()

    # Rank within the annotation (1 = highest confidence prediction)
    rank = models.PositiveIntegerField()

    class Meta:
        ordering = ["rank"]
        unique_together = [("annotation", "rank")]

    def __str__(self):
        return f"Prediction(rank={self.rank}, {self.scientific_name}, conf={self.confidence:.2f})"
