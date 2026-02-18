"""
Tests for obscured privacy setting with random point perturbation
"""

import json
import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from siteapps.socialmedia.geo_utils import (CONTINENTAL_US_CENTER_LAT,
                                            CONTINENTAL_US_CENTER_LON)
from siteapps.socialmedia.models import MediaPost
from siteapps.species.models import SpeciesName

User = get_user_model()


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371

    return c * r


class ObscuredPrivacyTestCase(TestCase):
    """Test obscured privacy setting with random point perturbation"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.test_email = "obscured_test@example.com"
        self.test_password = "testpassword123"
        self.user = User.objects.create(email=self.test_email, name="Test User")
        self.user.set_password(self.test_password)
        self.user.save()

        # Create API client
        self.client = APIClient()
        login_response = self.client.post(
            "/v1/users/login/", {"email": self.test_email, "password": self.test_password}, format="json"
        )
        token = json.loads(login_response.content)["key"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

        # Create test species
        self.species = SpeciesName.objects.create(name="Gray Wolf", scientific_name="Canis lupus")

    def test_obscured_post_creates_true_location_spatial(self):
        """Test that obscured posts create true_location_spatial field"""
        post_data = {
            "postTitle": "Wolf Sighting - Obscured",
            "privacySetting": "obscured",
            "latitude": 45.5231,
            "longitude": -122.6765,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
            "obfuscationKilometers": 5.0,
            "corner1Latitude": 45.52,
            "corner1Longitude": -122.68,
            "corner2Latitude": 45.53,
            "corner2Longitude": -122.68,
            "corner3Latitude": 45.53,
            "corner3Longitude": -122.67,
            "corner4Latitude": 45.52,
            "corner4Longitude": -122.67,
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)

        # Get the created post
        post = MediaPost.objects.filter(
            true_location_latitude=45.5231, true_location_longitude=-122.6765, geoprivacy="obscured"
        ).first()

        self.assertIsNotNone(post)
        self.assertIsNotNone(post.true_location_spatial)
        self.assertEqual(post.obfuscation_range_kilometers, 5.0)

    def test_obscured_retrieval_perturbs_location(self):
        """Test that retrieving obscured posts returns perturbed location"""
        # Create an obscured post
        true_lat = 40.7128
        true_lon = -74.0060
        obfuscation_km = 5.0

        post_data = {
            "postTitle": "Obscured Test",
            "privacySetting": "obscured",
            "latitude": true_lat,
            "longitude": true_lon,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
            "obfuscationKilometers": obfuscation_km,
            "corner1Latitude": 40.71,
            "corner1Longitude": -74.01,
            "corner2Latitude": 40.72,
            "corner2Longitude": -74.01,
            "corner3Latitude": 40.72,
            "corner3Longitude": -74.00,
            "corner4Latitude": 40.71,
            "corner4Longitude": -74.00,
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        # Retrieve the post via API
        response = self.client.post("/v1/socialmedia/api/feed/get/", json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        posts = data["results"]

        # Find our post
        our_post = None
        for post in posts:
            if post["title"] == "Obscured Test":
                our_post = post
                break

        self.assertIsNotNone(our_post)

        # The returned location should be perturbed (not the same as true location)
        returned_lat = our_post["latitude"]
        returned_lon = our_post["longitude"]

        # Calculate distance between true and returned location
        distance = haversine_distance(true_lat, true_lon, returned_lat, returned_lon)

        # Distance should be within the obfuscation range
        self.assertLessEqual(distance, obfuscation_km)

    def test_obscured_perturbation_multiple_retrievals(self):
        """Test that multiple retrievals return different perturbed locations"""
        # Create an obscured post
        true_lat = 34.0522
        true_lon = -118.2437
        obfuscation_km = 10.0

        post_data = {
            "postTitle": "Multi-Retrieval Test",
            "privacySetting": "obscured",
            "latitude": true_lat,
            "longitude": true_lon,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
            "obfuscationKilometers": obfuscation_km,
            "corner1Latitude": 34.05,
            "corner1Longitude": -118.25,
            "corner2Latitude": 34.06,
            "corner2Longitude": -118.25,
            "corner3Latitude": 34.06,
            "corner3Longitude": -118.24,
            "corner4Latitude": 34.05,
            "corner4Longitude": -118.24,
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        # Retrieve the post multiple times
        locations = []
        for _ in range(5):
            response = self.client.post(
                "/v1/socialmedia/api/feed/get/", json.dumps({}), content_type="application/json"
            )
            data = json.loads(response.content)
            posts = data["results"]

            # Find our post
            for post in posts:
                if post["title"] == "Multi-Retrieval Test":
                    locations.append((post["latitude"], post["longitude"]))
                    break

        # All retrievals should return different locations (randomized)
        # There's a very small chance they could be identical, but extremely unlikely
        unique_locations = set(locations)
        self.assertGreater(len(unique_locations), 1, "Perturbation should be randomized across retrievals")

        # All locations should be within the obfuscation range
        for lat, lon in locations:
            distance = haversine_distance(true_lat, true_lon, lat, lon)
            self.assertLessEqual(distance, obfuscation_km)

    def test_obscured_various_obfuscation_ranges(self):
        """Test obscured privacy with various obfuscation ranges"""
        # Test different obfuscation ranges (limited to 1-10 km per validation)
        obfuscation_ranges = [1.0, 2.0, 5.0, 8.0, 10.0]

        for obfuscation_km in obfuscation_ranges:
            # Create test location in continental US
            test_lat = 39.8283  # Near center of US
            test_lon = -98.5795

            post_data = {
                "postTitle": f"Test {obfuscation_km}km",
                "privacySetting": "obscured",
                "latitude": test_lat,
                "longitude": test_lon,
                "accuracyMeters": 10,
                "encounterDatetime": timezone.now().isoformat(),
                "geocodedLocationCountry": "USA",
                "species": "Gray Wolf",
                "obfuscationKilometers": obfuscation_km,
                "corner1Latitude": test_lat - 0.01,
                "corner1Longitude": test_lon - 0.01,
                "corner2Latitude": test_lat + 0.01,
                "corner2Longitude": test_lon - 0.01,
                "corner3Latitude": test_lat + 0.01,
                "corner3Longitude": test_lon + 0.01,
                "corner4Latitude": test_lat - 0.01,
                "corner4Longitude": test_lon + 0.01,
            }

            response = self.client.post(
                "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
            )
            self.assertEqual(response.status_code, 201)

            # Retrieve and verify
            response = self.client.post(
                "/v1/socialmedia/api/feed/get/", json.dumps({}), content_type="application/json"
            )
            data = json.loads(response.content)
            posts = data["results"]

            # Find our post
            for post in posts:
                if post["title"] == f"Test {obfuscation_km}km":
                    returned_lat = post["latitude"]
                    returned_lon = post["longitude"]

                    # Calculate distance
                    distance = haversine_distance(test_lat, test_lon, returned_lat, returned_lon)

                    # Distance should be within the obfuscation range (with small margin for rounding)
                    self.assertLessEqual(
                        distance, obfuscation_km + 0.01, f"Distance {distance}km exceeds obfuscation {obfuscation_km}km"
                    )
                    break

    def test_obscured_points_within_us_bounds(self):
        """Test that obscured points at various US locations stay within reasonable bounds"""
        # Test locations across the continental US
        test_locations = [
            (47.6062, -122.3321, "Seattle, WA"),
            (40.7128, -74.0060, "New York, NY"),
            (34.0522, -118.2437, "Los Angeles, CA"),
            (41.8781, -87.6298, "Chicago, IL"),
            (29.7604, -95.3698, "Houston, TX"),
            (33.4484, -112.0740, "Phoenix, AZ"),
            (39.7392, -104.9903, "Denver, CO"),
            (25.7617, -80.1918, "Miami, FL"),
        ]

        obfuscation_km = 10.0

        for test_lat, test_lon, location_name in test_locations:
            post_data = {
                "postTitle": f"Test {location_name}",
                "privacySetting": "obscured",
                "latitude": test_lat,
                "longitude": test_lon,
                "accuracyMeters": 10,
                "encounterDatetime": timezone.now().isoformat(),
                "geocodedLocationCountry": "USA",
                "species": "Gray Wolf",
                "obfuscationKilometers": obfuscation_km,
                "corner1Latitude": test_lat - 0.01,
                "corner1Longitude": test_lon - 0.01,
                "corner2Latitude": test_lat + 0.01,
                "corner2Longitude": test_lon - 0.01,
                "corner3Latitude": test_lat + 0.01,
                "corner3Longitude": test_lon + 0.01,
                "corner4Latitude": test_lat - 0.01,
                "corner4Longitude": test_lon + 0.01,
            }

            response = self.client.post(
                "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
            )
            self.assertEqual(response.status_code, 201, f"Failed to create post for {location_name}")

            # Retrieve and verify
            response = self.client.post(
                "/v1/socialmedia/api/feed/get/", json.dumps({}), content_type="application/json"
            )
            data = json.loads(response.content)
            posts = data["results"]

            # Find our post
            for post in posts:
                if post["title"] == f"Test {location_name}":
                    returned_lat = post["latitude"]
                    returned_lon = post["longitude"]

                    # Verify coordinates are within valid ranges
                    self.assertGreaterEqual(returned_lat, -90.0, f"Latitude out of range for {location_name}")
                    self.assertLessEqual(returned_lat, 90.0, f"Latitude out of range for {location_name}")
                    self.assertGreaterEqual(returned_lon, -180.0, f"Longitude out of range for {location_name}")
                    self.assertLessEqual(returned_lon, 180.0, f"Longitude out of range for {location_name}")

                    # Calculate distance
                    distance = haversine_distance(test_lat, test_lon, returned_lat, returned_lon)

                    # Distance should be within the obfuscation range
                    self.assertLessEqual(
                        distance, obfuscation_km + 0.01, f"Distance exceeds obfuscation for {location_name}"
                    )
                    break

    def test_private_returns_continental_us_center(self):
        """Test that private posts return the center of continental US"""
        # Create a private post
        true_lat = 40.7128
        true_lon = -74.0060

        post_data = {
            "postTitle": "Private Test",
            "privacySetting": "private",
            "latitude": true_lat,
            "longitude": true_lon,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        # Retrieve the post via API
        response = self.client.post("/v1/socialmedia/api/feed/get/", json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        posts = data["results"]

        # Find our post
        our_post = None
        for post in posts:
            if post["title"] == "Private Test":
                our_post = post
                break

        self.assertIsNotNone(our_post)

        # The returned location should be the center of continental US
        returned_lat = our_post["latitude"]
        returned_lon = our_post["longitude"]

        self.assertAlmostEqual(returned_lat, CONTINENTAL_US_CENTER_LAT, places=4)
        self.assertAlmostEqual(returned_lon, CONTINENTAL_US_CENTER_LON, places=4)

    def test_public_returns_exact_location(self):
        """Test that public posts return the exact true location"""
        # Create a public post
        true_lat = 34.0522
        true_lon = -118.2437

        post_data = {
            "postTitle": "Public Test",
            "privacySetting": "public",
            "latitude": true_lat,
            "longitude": true_lon,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        # Retrieve the post via API
        response = self.client.post("/v1/socialmedia/api/feed/get/", json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        posts = data["results"]

        # Find our post
        our_post = None
        for post in posts:
            if post["title"] == "Public Test":
                our_post = post
                break

        self.assertIsNotNone(our_post)

        # The returned location should match the true location exactly
        returned_lat = our_post["latitude"]
        returned_lon = our_post["longitude"]

        self.assertAlmostEqual(returned_lat, true_lat, places=4)
        self.assertAlmostEqual(returned_lon, true_lon, places=4)
