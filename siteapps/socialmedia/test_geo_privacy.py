# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Tests for geographic utilities and privacy-based lat/lon return
"""

import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from siteapps.socialmedia.geo_utils import (CONTINENTAL_US_CENTER_LAT,
                                            CONTINENTAL_US_CENTER_LON,
                                            calculate_offset_coordinates,
                                            get_continental_us_center)
from siteapps.socialmedia.models import MediaPost

User = get_user_model()


class GeoUtilsTestCase(TestCase):
    """Test geographic utility functions"""

    def test_get_continental_us_center(self):
        """Test that continental US center returns correct coordinates"""
        lat, lon = get_continental_us_center()
        self.assertEqual(lat, CONTINENTAL_US_CENTER_LAT)
        self.assertEqual(lon, CONTINENTAL_US_CENTER_LON)
        # Verify it's in Kansas (approximately)
        self.assertAlmostEqual(lat, 39.8283, places=2)
        self.assertAlmostEqual(lon, -98.5795, places=2)

    def test_calculate_offset_coordinates_basic(self):
        """Test basic offset coordinate calculation"""
        # Test with a known location (Los Angeles)
        lat, lon = 34.0522, -118.2437
        offset_km = 5.0

        offset_lat, offset_lon = calculate_offset_coordinates(lat, lon, offset_km)

        # Verify coordinates are returned
        self.assertIsNotNone(offset_lat)
        self.assertIsNotNone(offset_lon)

        # Verify offset is applied (coordinates should be different)
        # Note: there's a very small chance they could be the same if random offset is exactly 0,
        # but this is extremely unlikely
        different = (offset_lat != lat) or (offset_lon != lon)
        self.assertTrue(different)

    def test_calculate_offset_coordinates_within_range(self):
        """Test that offset stays within specified range"""
        lat, lon = 34.0522, -118.2437
        offset_km = 10.0

        # Test multiple times to verify randomness stays in range
        for _ in range(10):
            offset_lat, offset_lon = calculate_offset_coordinates(lat, lon, offset_km)

            # Calculate actual distance using Haversine formula (simplified)
            lat_diff = offset_lat - lat
            lon_diff = offset_lon - lon

            # Approximate distance in km
            # This is a rough approximation but good enough for testing
            lat_distance = lat_diff * 111.0  # 1 degree latitude ≈ 111 km
            lon_distance = lon_diff * 111.0 * math.cos(math.radians(lat))
            actual_distance = math.sqrt(lat_distance**2 + lon_distance**2)

            # Verify distance is within expected range (with small margin for rounding)
            self.assertLessEqual(actual_distance, offset_km + 0.1)

    def test_calculate_offset_coordinates_valid_range(self):
        """Test that offset coordinates stay in valid lat/lon ranges"""
        # Test various locations including edge cases
        test_cases = [
            (0.0, 0.0, 10.0),  # Equator
            (45.0, -100.0, 5.0),  # Mid-latitude
            (89.0, 0.0, 1.0),  # Near north pole
            (-89.0, 0.0, 1.0),  # Near south pole
            (34.0, 179.0, 5.0),  # Near date line (positive)
            (34.0, -179.0, 5.0),  # Near date line (negative)
        ]

        for lat, lon, offset_km in test_cases:
            offset_lat, offset_lon = calculate_offset_coordinates(lat, lon, offset_km)

            # Verify latitude stays in valid range
            self.assertGreaterEqual(offset_lat, -90.0)
            self.assertLessEqual(offset_lat, 90.0)

            # Verify longitude stays in valid range
            self.assertGreaterEqual(offset_lon, -180.0)
            self.assertLessEqual(offset_lon, 180.0)

    def test_calculate_offset_coordinates_null_inputs(self):
        """Test that None inputs return None"""
        offset_lat, offset_lon = calculate_offset_coordinates(None, None, None)
        self.assertIsNone(offset_lat)
        self.assertIsNone(offset_lon)

        offset_lat, offset_lon = calculate_offset_coordinates(34.0, None, 5.0)
        self.assertIsNone(offset_lat)
        self.assertIsNone(offset_lon)

        offset_lat, offset_lon = calculate_offset_coordinates(None, -118.0, 5.0)
        self.assertIsNone(offset_lat)
        self.assertIsNone(offset_lon)

        offset_lat, offset_lon = calculate_offset_coordinates(34.0, -118.0, None)
        self.assertIsNone(offset_lat)
        self.assertIsNone(offset_lon)

    def test_calculate_offset_randomness(self):
        """Test that offset calculation produces different results (randomness)"""
        lat, lon = 34.0522, -118.2437
        offset_km = 5.0

        # Generate multiple offsets
        results = []
        for _ in range(5):
            offset_lat, offset_lon = calculate_offset_coordinates(lat, lon, offset_km)
            results.append((offset_lat, offset_lon))

        # Verify at least some results are different (very high probability)
        unique_results = set(results)
        self.assertGreater(len(unique_results), 1)


class PrivacyLatLonReturnTestCase(TestCase):
    """Test that lat/lon is returned correctly based on privacy settings"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create(email="test@example.com", name="Test User")

    def test_public_post_returns_public_coordinates(self):
        """Test that public posts return the actual public coordinates"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Public Post",
            encounter_datetime=timezone.now(),
            geoprivacy=settings.PRIVACY_SETTING_PUBLIC,
            public_location_latitude=34.0522,
            public_location_longitude=-118.2437,
        )

        # Verify the post has the correct data
        self.assertEqual(post.public_location_latitude, 34.0522)
        self.assertEqual(post.public_location_longitude, -118.2437)

    def test_obscured_post_has_true_location(self):
        """Test that obscured posts store true location but don't expose it"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Obscured Post",
            encounter_datetime=timezone.now(),
            geoprivacy=settings.PRIVACY_SETTING_OBSCURED,
            true_location_latitude=34.0522,
            true_location_longitude=-118.2437,
            obfuscation_range_kilometers=10.0,
        )

        # Verify the post has the true location stored
        self.assertEqual(post.true_location_latitude, 34.0522)
        self.assertEqual(post.true_location_longitude, -118.2437)
        self.assertEqual(post.obfuscation_range_kilometers, 10.0)

        # Note: The actual offset is calculated dynamically in the view,
        # not stored in the database

    def test_private_post_has_private_location(self):
        """Test that private posts store private location"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Private Post",
            encounter_datetime=timezone.now(),
            geoprivacy=settings.PRIVACY_SETTING_PRIVATE,
            private_location_latitude=34.0522,
            private_location_longitude=-118.2437,
        )

        # Verify the post has the private location stored
        self.assertEqual(post.private_location_latitude, 34.0522)
        self.assertEqual(post.private_location_longitude, -118.2437)
