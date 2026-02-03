"""
Tests for application info endpoints.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class VersionInfoViewTestCase(TestCase):
    """Test version info endpoint"""

    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
        self.url = reverse("version_info")

    def test_get_version_info(self):
        """Test that version info endpoint returns correct structure"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("commit_hash", response.data)
        self.assertIn("release_tag", response.data)

    def test_version_info_no_authentication_required(self):
        """Test that version info endpoint does not require authentication"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_version_info_returns_strings(self):
        """Test that version info returns string values"""
        response = self.client.get(self.url)

        self.assertIsInstance(response.data["commit_hash"], str)
        self.assertIsInstance(response.data["release_tag"], str)

    def test_version_info_get_only(self):
        """Test that version info endpoint only accepts GET requests"""
        post_response = self.client.post(self.url)
        put_response = self.client.put(self.url)
        delete_response = self.client.delete(self.url)

        self.assertEqual(post_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
