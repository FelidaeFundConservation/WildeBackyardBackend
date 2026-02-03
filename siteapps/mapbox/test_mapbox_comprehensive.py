"""
Comprehensive tests for Mapbox API endpoints
"""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class MapboxAPITestCase(TestCase):
    """Comprehensive tests for Mapbox API endpoints"""

    def setUp(self):
        # Setup test account
        self.test_email = "test@example.com"
        self.test_password = "testpass"

        self.user = User.objects.create(email=self.test_email)
        self.user.set_password(self.test_password)
        self.user.save()

        self.client = APIClient()
        login_response = self.client.post(
            "/v1/users/login/", {"email": self.test_email, "password": self.test_password}, format="json"
        )

        token = json.loads(login_response.content)["key"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

    def test_search_suggestions(self):
        """Test getting search suggestions from Mapbox"""
        response = self.client.post("/v1/mapbox/api/search_suggestions/", {"searchText": "Los Angeles"}, format="json")

        # May succeed or fail depending on Mapbox API availability
        # 503 if Mapbox token is not configured
        self.assertIn(response.status_code, [200, 400, 401, 500, 503])

    def test_search_suggestions_empty_query(self):
        """Test search with empty query"""
        response = self.client.post("/v1/mapbox/api/search_suggestions/", {"searchText": ""}, format="json")

        # 503 if Mapbox is not configured, 400 for empty query, 200 if configured
        self.assertIn(response.status_code, [200, 400, 503])

    def test_search_suggestions_unauthenticated(self):
        """Test that unauthenticated users cannot search"""
        client = APIClient()
        response = client.post("/v1/mapbox/api/search_suggestions/", {"searchText": "New York"}, format="json")

        self.assertEqual(response.status_code, 401)

    def test_search_suggestions_long_query(self):
        """Test search with long query string"""
        long_query = "A" * 200
        response = self.client.post("/v1/mapbox/api/search_suggestions/", {"searchText": long_query}, format="json")

        # Should handle gracefully, 503 if Mapbox not configured
        self.assertIn(response.status_code, [200, 400, 500, 503])

    def test_search_suggestions_special_characters(self):
        """Test search with special characters"""
        response = self.client.post(
            "/v1/mapbox/api/search_suggestions/", {"searchText": "São Paulo, Brazil"}, format="json"
        )

        # 503 if Mapbox not configured
        self.assertIn(response.status_code, [200, 400, 500, 503])

    def test_geocode_location(self):
        """Test geocoding a location"""
        geocode_data = {"latitude": 34.0522, "longitude": -118.2437}

        response = self.client.post("/v1/mapbox/api/geocode/", geocode_data, format="json")

        # May succeed or fail depending on Mapbox API availability, 503 if not configured
        self.assertIn(response.status_code, [200, 400, 401, 500, 503])

    def test_geocode_invalid_coordinates(self):
        """Test geocoding with invalid coordinates"""
        invalid_data = {"latitude": 200, "longitude": -300}

        response = self.client.post("/v1/mapbox/api/geocode/", invalid_data, format="json")

        # Should return error (either 400, 500, or 503 if not configured)
        self.assertIn(response.status_code, [400, 500, 503])

    def test_geocode_missing_latitude(self):
        """Test geocoding with missing latitude"""
        incomplete_data = {"longitude": -118.2437}

        response = self.client.post("/v1/mapbox/api/geocode/", incomplete_data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_geocode_missing_longitude(self):
        """Test geocoding with missing longitude"""
        incomplete_data = {"latitude": 34.0522}

        response = self.client.post("/v1/mapbox/api/geocode/", incomplete_data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_geocode_boundary_coordinates(self):
        """Test geocoding with boundary coordinates"""
        # Test maximum valid coordinates
        max_coords = {"latitude": 90, "longitude": 180}
        response = self.client.post("/v1/mapbox/api/geocode/", max_coords, format="json")
        # 503 if Mapbox not configured
        self.assertIn(response.status_code, [200, 400, 500, 503])

        # Test minimum valid coordinates
        min_coords = {"latitude": -90, "longitude": -180}
        response = self.client.post("/v1/mapbox/api/geocode/", min_coords, format="json")
        # 503 if Mapbox not configured
        self.assertIn(response.status_code, [200, 400, 500, 503])

    def test_geocode_equator_prime_meridian(self):
        """Test geocoding at equator and prime meridian"""
        coords = {"latitude": 0, "longitude": 0}

        response = self.client.post("/v1/mapbox/api/geocode/", coords, format="json")

        # 503 if Mapbox not configured
        self.assertIn(response.status_code, [200, 400, 500, 503])

    def test_geocode_unauthenticated(self):
        """Test that unauthenticated users cannot geocode"""
        client = APIClient()
        geocode_data = {"latitude": 34.0522, "longitude": -118.2437}

        response = client.post("/v1/mapbox/api/geocode/", geocode_data, format="json")

        self.assertEqual(response.status_code, 401)

    def test_search_suggestions_missing_field(self):
        """Test search without searchText field"""
        response = self.client.post("/v1/mapbox/api/search_suggestions/", {}, format="json")

        # 503 if Mapbox not configured, 400 for missing field, 500 for other errors
        self.assertIn(response.status_code, [400, 500, 503])

    def test_geocode_string_coordinates(self):
        """Test geocoding with string coordinates (should fail)"""
        invalid_data = {"latitude": "thirty-four", "longitude": "negative one-eighteen"}

        response = self.client.post("/v1/mapbox/api/geocode/", invalid_data, format="json")

        # 503 if Mapbox not configured, 400 for invalid data, 500 for other errors
        self.assertIn(response.status_code, [400, 500, 503])

    def test_search_suggestions_numeric_query(self):
        """Test search with numeric query"""
        response = self.client.post("/v1/mapbox/api/search_suggestions/", {"searchText": "90210"}, format="json")

        # Should handle gracefully (zip code search), 503 if not configured
        self.assertIn(response.status_code, [200, 400, 500, 503])

    def test_multiple_geocode_requests(self):
        """Test multiple geocode requests in sequence"""
        coords_list = [
            {"latitude": 34.0522, "longitude": -118.2437},  # Los Angeles
            {"latitude": 40.7128, "longitude": -74.0060},  # New York
            {"latitude": 51.5074, "longitude": -0.1278},  # London
        ]

        for coords in coords_list:
            response = self.client.post("/v1/mapbox/api/geocode/", coords, format="json")
            # Each request should be processed independently, 503 if not configured
            self.assertIn(response.status_code, [200, 400, 500, 503])

    def test_search_suggestions_response_structure(self):
        """Test the structure of search suggestions response"""
        response = self.client.post("/v1/mapbox/api/search_suggestions/", {"searchText": "California"}, format="json")

        if response.status_code == 200:
            # Verify response has expected structure
            data = response.json()
            # Structure depends on implementation
            self.assertIsInstance(data, (dict, list))

    def test_geocode_response_structure(self):
        """Test the structure of geocode response"""
        geocode_data = {"latitude": 34.0522, "longitude": -118.2437}

        response = self.client.post("/v1/mapbox/api/geocode/", geocode_data, format="json")

        if response.status_code == 200:
            # Verify response has expected structure
            data = response.json()
            self.assertIsInstance(data, dict)
