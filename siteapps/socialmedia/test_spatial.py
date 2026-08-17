# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Tests for GeoDjango PostGIS spatial functionality
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from siteapps.socialmedia.models import MediaPost
from siteapps.species.models import SpeciesName

User = get_user_model()


class SpatialFieldsTestCase(TestCase):
    """Test spatial fields functionality"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.test_email = "spatial_test@example.com"
        self.test_password = "testpassword123"
        self.user = User.objects.create(email=self.test_email)
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

    def test_public_location_spatial_field_created(self):
        """Test that true_location_spatial is created for public posts"""
        post_data = {
            "postTitle": "Wolf Sighting",
            "privacySetting": "public",
            "latitude": 45.5231,
            "longitude": -122.6765,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)

        # Get the created post
        post = MediaPost.objects.filter(public_location_latitude=45.5231, public_location_longitude=-122.6765).first()

        self.assertIsNotNone(post)
        # true_location_spatial should be set for public posts
        self.assertIsNotNone(post.true_location_spatial)

        # Verify the spatial field has correct coordinates
        # Note: Point is (longitude, latitude) - order matters!
        expected_point = Point(-122.6765, 45.5231, srid=4326)
        # true_location_spatial should match for public posts
        self.assertEqual(post.true_location_spatial, expected_point)

        # Verify latitude and longitude are correct
        self.assertAlmostEqual(post.true_location_spatial.y, 45.5231, places=4)
        self.assertAlmostEqual(post.true_location_spatial.x, -122.6765, places=4)

    def test_true_location_spatial_field_created(self):
        """Test that true_location_spatial is created for obscured posts"""
        post_data = {
            "postTitle": "Wolf Sighting - Obscured",
            "privacySetting": "obscured",
            "latitude": 47.6062,
            "longitude": -122.3321,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
            "obfuscationKilometers": 5.0,
            "corner1Latitude": 47.60,
            "corner1Longitude": -122.34,
            "corner2Latitude": 47.61,
            "corner2Longitude": -122.34,
            "corner3Latitude": 47.61,
            "corner3Longitude": -122.32,
            "corner4Latitude": 47.60,
            "corner4Longitude": -122.32,
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )

        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content}")
        self.assertEqual(response.status_code, 201)

        # Get the created post
        post = MediaPost.objects.filter(true_location_spatial__isnull=False).first()

        self.assertIsNotNone(post)
        self.assertIsNotNone(post.true_location_spatial)

        # Verify the spatial field has correct coordinates
        expected_point = Point(-122.3321, 47.6062, srid=4326)
        self.assertEqual(post.true_location_spatial, expected_point)

        # Verify latitude and longitude are correct
        self.assertAlmostEqual(post.true_location_spatial.y, 47.6062, places=4)
        self.assertAlmostEqual(post.true_location_spatial.x, -122.3321, places=4)

    def test_private_location_spatial_field_created(self):
        """Test that true_location_spatial is created for private posts"""
        post_data = {
            "postTitle": "Wolf Sighting - Private",
            "privacySetting": "private",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracyMeters": 5,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "USA",
            "species": "Gray Wolf",
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)

        # Get the created post
        post = MediaPost.objects.filter(true_location_spatial__isnull=False, geoprivacy="private").first()

        self.assertIsNotNone(post)
        # true_location_spatial should be set for private posts
        self.assertIsNotNone(post.true_location_spatial)

        # Verify the spatial field has correct coordinates
        expected_point = Point(-74.0060, 40.7128, srid=4326)
        # true_location_spatial should match for private posts
        self.assertEqual(post.true_location_spatial, expected_point)

        # Verify latitude and longitude are correct
        self.assertAlmostEqual(post.true_location_spatial.y, 40.7128, places=4)
        self.assertAlmostEqual(post.true_location_spatial.x, -74.0060, places=4)

    def test_spatial_field_srid(self):
        """Test that true_location_spatial uses correct SRID (4326 - WGS84)"""
        post_data = {
            "postTitle": "Test SRID",
            "privacySetting": "public",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "accuracyMeters": 10,
            "encounterDatetime": timezone.now().isoformat(),
            "geocodedLocationCountry": "UK",
        }

        response = self.client.post(
            "/v1/socialmedia/api/posts/create/", json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)

        post = MediaPost.objects.filter(public_location_latitude=51.5074, public_location_longitude=-0.1278).first()

        self.assertIsNotNone(post)
        self.assertIsNotNone(post.true_location_spatial)
        self.assertEqual(post.true_location_spatial.srid, 4326)

    def test_spatial_fields_none_when_no_location(self):
        """Test that true_location_spatial remains None when no location provided"""
        # Create a post directly without going through the API
        # (to bypass validation that requires location)
        post = MediaPost.objects.create(
            title="No Location Post",
            encounter_datetime=timezone.now(),
            geoprivacy="public",
            accuracy_ring_radius_meters=10,
            geocoded_location_country="USA",
            created_by=self.user,
        )

        self.assertIsNone(post.public_location_latitude)
        self.assertIsNone(post.public_location_longitude)
        self.assertIsNone(post.true_location_spatial)


class ManagementCommandTestCase(TestCase):
    """Test populate_spatial_fields management command"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(email="command_test@example.com")

    def test_populate_spatial_fields_from_existing_data(self):
        """Test that management command populates true_location_spatial from lat/lng"""
        # Create posts with lat/lng but no spatial fields
        post1 = MediaPost.objects.create(
            title="Post 1",
            encounter_datetime=timezone.now(),
            geoprivacy="public",
            accuracy_ring_radius_meters=10,
            geocoded_location_country="USA",
            public_location_latitude=34.0522,
            public_location_longitude=-118.2437,            created_by=self.user,
        )

        post2 = MediaPost.objects.create(
            title="Post 2",
            encounter_datetime=timezone.now(),
            geoprivacy="obscured",
            accuracy_ring_radius_meters=10,
            geocoded_location_country="USA",            created_by=self.user,
        )

        post3 = MediaPost.objects.create(
            title="Post 3",
            encounter_datetime=timezone.now(),
            geoprivacy="private",
            accuracy_ring_radius_meters=10,
            geocoded_location_country="USA",            private_location_longitude=-122.4194,            created_by=self.user,
        )

        # Verify spatial fields are None initially
        self.assertIsNone(post1.true_location_spatial)
        self.assertIsNone(post2.true_location_spatial)
        self.assertIsNone(post3.true_location_spatial)

        # Run the management command
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("populate_spatial_fields", stdout=out)

        # Refresh from database
        post1.refresh_from_db()
        post2.refresh_from_db()
        post3.refresh_from_db()

        # Verify true_location_spatial fields are now populated for all posts
        self.assertIsNotNone(post1.true_location_spatial)
        self.assertEqual(post1.true_location_spatial, Point(-118.2437, 34.0522, srid=4326))

        self.assertIsNotNone(post2.true_location_spatial)
        self.assertEqual(post2.true_location_spatial, Point(-74.0060, 40.7128, srid=4326))

        self.assertIsNotNone(post3.true_location_spatial)
        self.assertEqual(post3.true_location_spatial, Point(-122.4194, 37.7749, srid=4326))

    def test_populate_spatial_fields_dry_run(self):
        """Test that dry run mode doesn't save changes"""
        post = MediaPost.objects.create(
            title="Dry Run Test",
            encounter_datetime=timezone.now(),
            geoprivacy="public",
            accuracy_ring_radius_meters=10,
            geocoded_location_country="USA",
            public_location_latitude=34.0522,
            public_location_longitude=-118.2437,            created_by=self.user,
        )

        self.assertIsNone(post.true_location_spatial)

        # Run with dry-run flag
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("populate_spatial_fields", "--dry-run", stdout=out)

        # Refresh from database
        post.refresh_from_db()

        # Verify spatial field is still None (no changes saved)
        self.assertIsNone(post.true_location_spatial)
