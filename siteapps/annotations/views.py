import json

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.socialmedia.models import Media, MediaPost

from .models import (
    MegaDetectorAnnotation,
    MegaDetectorBoundingBox,
    SpeciesNetAnnotation,
    SpeciesNetPrediction,
)


def _serialize_bbox(bbox):
    return {
        "id": str(bbox.id),
        "category": bbox.category,
        "confidence": bbox.confidence,
        "bbox_x": bbox.bbox_x,
        "bbox_y": bbox.bbox_y,
        "bbox_width": bbox.bbox_width,
        "bbox_height": bbox.bbox_height,
    }


def _serialize_megadetector(annotation):
    return {
        "id": str(annotation.id),
        "media_id": str(annotation.media_id),
        "model_version": annotation.model_version,
        "max_detection_conf": annotation.max_detection_conf,
        "created": str(annotation.created),
        "bounding_boxes": [_serialize_bbox(b) for b in annotation.bounding_boxes.all()],
    }


def _serialize_prediction(pred):
    return {
        "rank": pred.rank,
        "scientific_name": pred.scientific_name,
        "common_name": pred.common_name,
        "confidence": pred.confidence,
    }


def _serialize_speciesnet(annotation):
    return {
        "id": str(annotation.id),
        "media_id": str(annotation.media_id),
        "megadetector_bbox_id": str(annotation.megadetector_bbox_id) if annotation.megadetector_bbox_id else None,
        "model_version": annotation.model_version,
        "created": str(annotation.created),
        "predictions": [_serialize_prediction(p) for p in annotation.predictions.all()],
    }


# ---------------------------------------------------------------------------
# MegaDetector endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    summary="Submit MegaDetector annotation",
    description=(
        "Store MegaDetector detection results for a media object. "
        "Accepts the bounding box list in MegaDetector format. "
        "Requires staff/admin privileges."
    ),
    request=inline_serializer(
        name="MegaDetectorCreateRequest",
        fields={
            "media_id": serializers.UUIDField(),
            "model_version": serializers.CharField(),
            "max_detection_conf": serializers.FloatField(required=False),
            "raw_result": serializers.JSONField(required=False),
            "bounding_boxes": serializers.ListField(
                child=inline_serializer(
                    name="BoundingBoxInput",
                    fields={
                        "category": serializers.ChoiceField(choices=["animal", "person", "vehicle"]),
                        "confidence": serializers.FloatField(),
                        "bbox_x": serializers.FloatField(),
                        "bbox_y": serializers.FloatField(),
                        "bbox_width": serializers.FloatField(),
                        "bbox_height": serializers.FloatField(),
                    },
                ),
                required=False,
            ),
        },
    ),
    responses={
        201: inline_serializer(
            name="MegaDetectorCreateResponse",
            fields={"annotation_id": serializers.UUIDField()},
        ),
        400: inline_serializer(name="ErrorResponse400MD", fields={"error": serializers.CharField()}),
    },
    tags=["Annotations"],
)
class CreateMegaDetectorAnnotationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        data = json.loads(request.body)

        media_id = data.get("media_id")
        model_version = data.get("model_version")

        if not media_id or not model_version:
            return Response(
                {"error": "media_id and model_version are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return Response({"error": "Media not found."}, status=status.HTTP_400_BAD_REQUEST)

        annotation = MegaDetectorAnnotation.objects.create(
            media=media,
            model_version=model_version,
            max_detection_conf=data.get("max_detection_conf"),
            raw_result=data.get("raw_result"),
        )

        valid_categories = {c[0] for c in MegaDetectorBoundingBox._meta.get_field("category").choices}
        for i, box in enumerate(data.get("bounding_boxes", [])):
            required_bbox_fields = ["category", "confidence", "bbox_x", "bbox_y", "bbox_width", "bbox_height"]
            missing = [f for f in required_bbox_fields if box.get(f) is None]
            if missing:
                annotation.delete()
                return Response(
                    {"error": f"Bounding box {i} is missing required fields: {missing}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if box["category"] not in valid_categories:
                annotation.delete()
                return Response(
                    {"error": f"Bounding box {i} has invalid category '{box['category']}'. Must be one of {sorted(valid_categories)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            MegaDetectorBoundingBox.objects.create(
                annotation=annotation,
                category=box["category"],
                confidence=box["confidence"],
                bbox_x=box["bbox_x"],
                bbox_y=box["bbox_y"],
                bbox_width=box["bbox_width"],
                bbox_height=box["bbox_height"],
            )

        return Response({"annotation_id": str(annotation.id)}, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Get MegaDetector annotations for a media object",
    description="Retrieve all MegaDetector annotation results stored for a given media ID.",
    responses={
        200: inline_serializer(
            name="MegaDetectorGetResponse",
            fields={"annotations": serializers.ListField(child=serializers.JSONField())},
        ),
        404: inline_serializer(name="ErrorResponse404MD", fields={"error": serializers.CharField()}),
    },
    tags=["Annotations"],
)
class GetMegaDetectorAnnotationsView(APIView):
    def get(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return Response({"error": "Media not found."}, status=status.HTTP_404_NOT_FOUND)

        annotations = MegaDetectorAnnotation.objects.filter(media=media).prefetch_related("bounding_boxes")
        return Response(
            {"annotations": [_serialize_megadetector(a) for a in annotations]},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# SpeciesNet endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    summary="Submit SpeciesNet annotation",
    description=(
        "Store SpeciesNet species classification results for a media object. "
        "Optionally linked to a specific MegaDetector bounding box (crop). "
        "Requires staff/admin privileges."
    ),
    request=inline_serializer(
        name="SpeciesNetCreateRequest",
        fields={
            "media_id": serializers.UUIDField(),
            "model_version": serializers.CharField(),
            "megadetector_bbox_id": serializers.UUIDField(required=False),
            "raw_result": serializers.JSONField(required=False),
            "predictions": serializers.ListField(
                child=inline_serializer(
                    name="SpeciesNetPredictionInput",
                    fields={
                        "scientific_name": serializers.CharField(),
                        "common_name": serializers.CharField(required=False),
                        "confidence": serializers.FloatField(),
                        "rank": serializers.IntegerField(),
                    },
                ),
                required=False,
            ),
        },
    ),
    responses={
        201: inline_serializer(
            name="SpeciesNetCreateResponse",
            fields={"annotation_id": serializers.UUIDField()},
        ),
        400: inline_serializer(name="ErrorResponse400SN", fields={"error": serializers.CharField()}),
    },
    tags=["Annotations"],
)
class CreateSpeciesNetAnnotationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        data = json.loads(request.body)

        media_id = data.get("media_id")
        model_version = data.get("model_version")

        if not media_id or not model_version:
            return Response(
                {"error": "media_id and model_version are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return Response({"error": "Media not found."}, status=status.HTTP_400_BAD_REQUEST)

        bbox = None
        bbox_id = data.get("megadetector_bbox_id")
        if bbox_id:
            try:
                bbox = MegaDetectorBoundingBox.objects.get(id=bbox_id)
            except MegaDetectorBoundingBox.DoesNotExist:
                return Response(
                    {"error": "MegaDetector bounding box not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        annotation = SpeciesNetAnnotation.objects.create(
            media=media,
            megadetector_bbox=bbox,
            model_version=model_version,
            raw_result=data.get("raw_result"),
        )

        for i, pred in enumerate(data.get("predictions", [])):
            required_pred_fields = ["scientific_name", "confidence", "rank"]
            missing = [f for f in required_pred_fields if pred.get(f) is None]
            if missing:
                annotation.delete()
                return Response(
                    {"error": f"Prediction {i} is missing required fields: {missing}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            SpeciesNetPrediction.objects.create(
                annotation=annotation,
                scientific_name=pred["scientific_name"],
                common_name=pred.get("common_name", ""),
                confidence=pred["confidence"],
                rank=pred["rank"],
            )

        return Response({"annotation_id": str(annotation.id)}, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Get SpeciesNet annotations for a media object",
    description="Retrieve all SpeciesNet annotation results stored for a given media ID.",
    responses={
        200: inline_serializer(
            name="SpeciesNetGetResponse",
            fields={"annotations": serializers.ListField(child=serializers.JSONField())},
        ),
        404: inline_serializer(name="ErrorResponse404SN", fields={"error": serializers.CharField()}),
    },
    tags=["Annotations"],
)
class GetSpeciesNetAnnotationsView(APIView):
    def get(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return Response({"error": "Media not found."}, status=status.HTTP_404_NOT_FOUND)

        annotations = SpeciesNetAnnotation.objects.filter(media=media).prefetch_related("predictions")
        return Response(
            {"annotations": [_serialize_speciesnet(a) for a in annotations]},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Combined post annotations endpoint
# ---------------------------------------------------------------------------


@extend_schema(
    summary="Get all annotations for a sighting post",
    description=(
        "Retrieve all MegaDetector and SpeciesNet annotations for the media "
        "attached to a given MediaPost (sighting)."
    ),
    responses={
        200: inline_serializer(
            name="PostAnnotationsResponse",
            fields={
                "megadetector": serializers.ListField(child=serializers.JSONField()),
                "speciesnet": serializers.ListField(child=serializers.JSONField()),
            },
        ),
        404: inline_serializer(name="ErrorResponse404Post", fields={"error": serializers.CharField()}),
    },
    tags=["Annotations"],
)
class GetPostAnnotationsView(APIView):
    def get(self, request, post_id):
        try:
            post = MediaPost.objects.select_related("media").get(id=post_id)
        except MediaPost.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

        if post.media is None:
            return Response(
                {"megadetector": [], "speciesnet": []},
                status=status.HTTP_200_OK,
            )

        media = post.media
        md_annotations = MegaDetectorAnnotation.objects.filter(media=media).prefetch_related("bounding_boxes")
        sn_annotations = SpeciesNetAnnotation.objects.filter(media=media).prefetch_related("predictions")

        return Response(
            {
                "megadetector": [_serialize_megadetector(a) for a in md_annotations],
                "speciesnet": [_serialize_speciesnet(a) for a in sn_annotations],
            },
            status=status.HTTP_200_OK,
        )
