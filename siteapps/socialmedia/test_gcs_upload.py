"""
Tests for Google Cloud Storage media upload functionality
"""

import base64
import hashlib
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from PIL import Image

from siteapps.socialmedia.views import create_media

User = get_user_model()


class GCSUploadTestCase(TestCase):
    """Test cases for Google Cloud Storage upload functionality"""

    def setUp(self):
        """Set up test user and media data"""
        self.user = User.objects.create(email="test@example.com")
        self.user.set_password("testpassword")
        self.user.save()

        # Create test image bytes
        test_image = Image.new("RGB", (100, 100), color="red")
        img_bytes_io = BytesIO()
        test_image.save(img_bytes_io, format="JPEG")
        self.test_image_bytes = img_bytes_io.getvalue()
        self.test_image_hash = hashlib.sha256(self.test_image_bytes).hexdigest()

        # Create test video bytes (minimal MP4 header)
        self.test_video_bytes = b"fake_video_content"
        self.test_video_hash = hashlib.sha256(self.test_video_bytes).hexdigest()

    @patch("siteapps.socialmedia.views.gcs_storage.Client")
    def test_create_media_uploads_image_to_gcs(self, mock_gcs_client):
        """Test that create_media uploads images to correct GCS path"""
        # Mock GCS
        mock_gcs_bucket = MagicMock()
        mock_gcs_blob = MagicMock()
        mock_gcs_client.return_value.bucket.return_value = mock_gcs_bucket
        mock_gcs_bucket.blob.return_value = mock_gcs_blob

        # Create media (image)
        request_mock = MagicMock()
        request_mock.user = self.user

        media = create_media(
            media_bytes=self.test_image_bytes,
            content_hash=self.test_image_hash,
            request=request_mock,
            is_video=False,
        )

        # Verify GCS client was called correctly
        mock_gcs_client.assert_called_once()
        mock_gcs_client.return_value.bucket.assert_called_once_with(settings.GCS_BUCKET_NAME)

        # Verify blob was created with correct path (images)
        expected_blob_name = f"{settings.GCS_IMAGES_PATH}/{self.test_image_hash}.JPEG"
        mock_gcs_bucket.blob.assert_called_once_with(expected_blob_name)

        # Verify upload was called
        mock_gcs_blob.upload_from_string.assert_called_once_with(
            self.test_image_bytes, content_type="image/jpeg"
        )

        # Verify Media object was created
        self.assertIsNotNone(media)
        self.assertEqual(media.content_hash, self.test_image_hash)
        self.assertFalse(media.is_video)
        self.assertEqual(media.uploaded_by, self.user)

    @patch("siteapps.socialmedia.views.gcs_storage.Client")
    def test_create_media_uploads_video_to_gcs(self, mock_gcs_client):
        """Test that create_media uploads videos to correct GCS path"""
        # Mock GCS
        mock_gcs_bucket = MagicMock()
        mock_gcs_blob = MagicMock()
        mock_gcs_client.return_value.bucket.return_value = mock_gcs_bucket
        mock_gcs_bucket.blob.return_value = mock_gcs_blob

        # Create media (video)
        request_mock = MagicMock()
        request_mock.user = self.user

        media = create_media(
            media_bytes=self.test_video_bytes,
            content_hash=self.test_video_hash,
            request=request_mock,
            is_video=True,
        )

        # Verify GCS client was called correctly
        mock_gcs_client.assert_called_once()
        mock_gcs_client.return_value.bucket.assert_called_once_with(settings.GCS_BUCKET_NAME)

        # Verify blob was created with correct path (videos)
        expected_blob_name = f"{settings.GCS_VIDEOS_PATH}/{self.test_video_hash}.MP4"
        mock_gcs_bucket.blob.assert_called_once_with(expected_blob_name)

        # Verify upload was called
        mock_gcs_blob.upload_from_string.assert_called_once_with(self.test_video_bytes, content_type="video/mp4")

        # Verify Media object was created
        self.assertIsNotNone(media)
        self.assertEqual(media.content_hash, self.test_video_hash)
        self.assertTrue(media.is_video)
        self.assertEqual(media.uploaded_by, self.user)

    @patch("siteapps.socialmedia.views.gcs_storage.Client")
    @patch("siteapps.socialmedia.views.logging")
    def test_create_media_handles_gcs_failure_gracefully(self, mock_logging, mock_gcs_client):
        """Test that create_media handles GCS upload failures gracefully"""
        # Mock GCS to raise an exception
        mock_gcs_client.return_value.bucket.side_effect = Exception("GCS connection failed")

        # Create media should still succeed (falls back to local path)
        request_mock = MagicMock()
        request_mock.user = self.user

        media = create_media(
            media_bytes=self.test_image_bytes,
            content_hash=self.test_image_hash,
            request=request_mock,
            is_video=False,
        )

        # Verify Media object was still created with local path
        self.assertIsNotNone(media)
        self.assertIn("local://", media.file_cloud_path)

        # Verify error was logged
        mock_logging.error.assert_called_once()
        self.assertIn("Failed to upload media to GCS", str(mock_logging.error.call_args))
