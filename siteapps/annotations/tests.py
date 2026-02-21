import json
import uuid

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from siteapps.annotations.models import (
    MegaDetectorAnnotation,
    MegaDetectorBoundingBox,
    SpeciesNetAnnotation,
    SpeciesNetPrediction,
)
from siteapps.socialmedia.models import Media, MediaPost
from siteapps.species.models import SpeciesName
from siteapps.users.models import User


class AnnotationsAPITestCase(TestCase):
    def setUp(self):
        test_email = "annotations_test@fakeemail.com"
        test_password = "fakepassword123"

        self.user = User.objects.create(email=test_email)
        self.user.set_password(test_password)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        self.client = APIClient()
        login_response = self.client.post(
            "/v1/users/login/", {"email": test_email, "password": test_password}, format="json"
        )
        token = json.loads(login_response.content)["key"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

        # Create a Media object to annotate
        self.media = Media.objects.create(
            is_video=False,
            file_cloud_path="https://storage.googleapis.com/test-bucket/test-image.jpg",
            content_hash="abc123",
            uploaded_by=self.user,
        )

        # Create a MediaPost linked to the media
        species = SpeciesName.objects.create(name="Test Species", scientific_name="Testus specius")
        self.post = MediaPost.objects.create(
            created_by=self.user,
            title="Test Post",
            media=self.media,
            encounter_datetime="2024-01-01T12:00:00",
            geoprivacy="public",
            public_location_latitude=40.0,
            public_location_longitude=-74.0,
            species=species,
        )

    # ------------------------------------------------------------------
    # MegaDetector create
    # ------------------------------------------------------------------

    def test_create_megadetector_annotation_success(self):
        payload = {
            "media_id": str(self.media.id),
            "model_version": "MDv5a",
            "max_detection_conf": 0.92,
            "bounding_boxes": [
                {
                    "category": "animal",
                    "confidence": 0.92,
                    "bbox_x": 0.1,
                    "bbox_y": 0.2,
                    "bbox_width": 0.3,
                    "bbox_height": 0.4,
                }
            ],
        }
        response = self.client.post(
            "/v1/annotations/api/megadetector/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertIn("annotation_id", data)

        annotation = MegaDetectorAnnotation.objects.get(id=data["annotation_id"])
        self.assertEqual(annotation.model_version, "MDv5a")
        self.assertEqual(annotation.bounding_boxes.count(), 1)
        bbox = annotation.bounding_boxes.first()
        self.assertEqual(bbox.category, "animal")
        self.assertAlmostEqual(bbox.confidence, 0.92)

    def test_create_megadetector_annotation_missing_fields(self):
        payload = {"media_id": str(self.media.id)}  # missing model_version
        response = self.client.post(
            "/v1/annotations/api/megadetector/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_megadetector_annotation_invalid_media(self):
        payload = {"media_id": str(uuid.uuid4()), "model_version": "MDv5a"}
        response = self.client.post(
            "/v1/annotations/api/megadetector/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_megadetector_annotation_invalid_bbox_category(self):
        payload = {
            "media_id": str(self.media.id),
            "model_version": "MDv5a",
            "bounding_boxes": [
                {
                    "category": "unknown_category",
                    "confidence": 0.9,
                    "bbox_x": 0.1,
                    "bbox_y": 0.1,
                    "bbox_width": 0.3,
                    "bbox_height": 0.3,
                }
            ],
        }
        response = self.client.post(
            "/v1/annotations/api/megadetector/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_megadetector_annotation_missing_bbox_fields(self):
        payload = {
            "media_id": str(self.media.id),
            "model_version": "MDv5a",
            "bounding_boxes": [
                # missing confidence and bbox coords
                {"category": "animal"}
            ],
        }
        response = self.client.post(
            "/v1/annotations/api/megadetector/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


        self.client.credentials()  # remove auth
        payload = {"media_id": str(self.media.id), "model_version": "MDv5a"}
        response = self.client.post(
            "/v1/annotations/api/megadetector/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # MegaDetector get
    # ------------------------------------------------------------------

    def test_get_megadetector_annotations(self):
        annotation = MegaDetectorAnnotation.objects.create(
            media=self.media,
            model_version="MDv5a",
            max_detection_conf=0.88,
        )
        MegaDetectorBoundingBox.objects.create(
            annotation=annotation,
            category="animal",
            confidence=0.88,
            bbox_x=0.0,
            bbox_y=0.0,
            bbox_width=0.5,
            bbox_height=0.5,
        )

        response = self.client.get(f"/v1/annotations/api/megadetector/{self.media.id}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["annotations"]), 1)
        self.assertEqual(len(data["annotations"][0]["bounding_boxes"]), 1)

    def test_get_megadetector_annotations_not_found(self):
        response = self.client.get(f"/v1/annotations/api/megadetector/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # SpeciesNet create
    # ------------------------------------------------------------------

    def _create_megadetector_bbox(self):
        annotation = MegaDetectorAnnotation.objects.create(
            media=self.media,
            model_version="MDv5a",
        )
        return MegaDetectorBoundingBox.objects.create(
            annotation=annotation,
            category="animal",
            confidence=0.9,
            bbox_x=0.1,
            bbox_y=0.1,
            bbox_width=0.4,
            bbox_height=0.4,
        )

    def test_create_speciesnet_annotation_success(self):
        bbox = self._create_megadetector_bbox()
        payload = {
            "media_id": str(self.media.id),
            "model_version": "v4.0.1",
            "megadetector_bbox_id": str(bbox.id),
            "predictions": [
                {"scientific_name": "Sciurus carolinensis", "common_name": "Eastern gray squirrel", "confidence": 0.85, "rank": 1},
                {"scientific_name": "Sciurus niger", "common_name": "Fox squirrel", "confidence": 0.10, "rank": 2},
            ],
        }
        response = self.client.post(
            "/v1/annotations/api/speciesnet/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertIn("annotation_id", data)

        annotation = SpeciesNetAnnotation.objects.get(id=data["annotation_id"])
        self.assertEqual(annotation.predictions.count(), 2)
        top = annotation.predictions.get(rank=1)
        self.assertEqual(top.scientific_name, "Sciurus carolinensis")
        self.assertAlmostEqual(top.confidence, 0.85)

    def test_create_speciesnet_annotation_no_bbox(self):
        payload = {
            "media_id": str(self.media.id),
            "model_version": "v4.0.1",
            "predictions": [
                {"scientific_name": "Ursus americanus", "common_name": "American black bear", "confidence": 0.95, "rank": 1},
            ],
        }
        response = self.client.post(
            "/v1/annotations/api/speciesnet/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_create_speciesnet_annotation_invalid_bbox(self):
        payload = {
            "media_id": str(self.media.id),
            "model_version": "v4.0.1",
            "megadetector_bbox_id": str(uuid.uuid4()),
        }
        response = self.client.post(
            "/v1/annotations/api/speciesnet/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_speciesnet_annotation_missing_prediction_fields(self):
        payload = {
            "media_id": str(self.media.id),
            "model_version": "v4.0.1",
            "predictions": [
                # missing confidence and rank
                {"scientific_name": "Canis lupus"}
            ],
        }
        response = self.client.post(
            "/v1/annotations/api/speciesnet/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_speciesnet_annotation_requires_auth(self):
        self.client.credentials()
        payload = {"media_id": str(self.media.id), "model_version": "v4.0.1"}
        response = self.client.post(
            "/v1/annotations/api/speciesnet/create/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # SpeciesNet get
    # ------------------------------------------------------------------

    def test_get_speciesnet_annotations(self):
        annotation = SpeciesNetAnnotation.objects.create(
            media=self.media,
            model_version="v4.0.1",
        )
        SpeciesNetPrediction.objects.create(
            annotation=annotation,
            scientific_name="Vulpes vulpes",
            common_name="Red fox",
            confidence=0.75,
            rank=1,
        )

        response = self.client.get(f"/v1/annotations/api/speciesnet/{self.media.id}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["annotations"]), 1)
        self.assertEqual(data["annotations"][0]["predictions"][0]["scientific_name"], "Vulpes vulpes")

    def test_get_speciesnet_annotations_not_found(self):
        response = self.client.get(f"/v1/annotations/api/speciesnet/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # Combined post annotations
    # ------------------------------------------------------------------

    def test_get_post_annotations(self):
        md_annotation = MegaDetectorAnnotation.objects.create(
            media=self.media,
            model_version="MDv5a",
        )
        MegaDetectorBoundingBox.objects.create(
            annotation=md_annotation,
            category="animal",
            confidence=0.9,
            bbox_x=0.0,
            bbox_y=0.0,
            bbox_width=0.5,
            bbox_height=0.5,
        )
        sn_annotation = SpeciesNetAnnotation.objects.create(
            media=self.media,
            model_version="v4.0.1",
        )
        SpeciesNetPrediction.objects.create(
            annotation=sn_annotation,
            scientific_name="Canis lupus",
            common_name="Gray wolf",
            confidence=0.80,
            rank=1,
        )

        response = self.client.get(f"/v1/annotations/api/post/{self.post.id}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["megadetector"]), 1)
        self.assertEqual(len(data["speciesnet"]), 1)

    def test_get_post_annotations_no_media(self):
        post_no_media = MediaPost.objects.create(
            created_by=self.user,
            title="No Media Post",
            media=None,
            encounter_datetime="2024-01-01T12:00:00",
            geoprivacy="public",
            public_location_latitude=40.0,
            public_location_longitude=-74.0,
        )
        response = self.client.get(f"/v1/annotations/api/post/{post_no_media.id}/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["megadetector"], [])
        self.assertEqual(data["speciesnet"], [])

    def test_get_post_annotations_not_found(self):
        response = self.client.get(f"/v1/annotations/api/post/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)
