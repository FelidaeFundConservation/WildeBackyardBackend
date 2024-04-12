import json

from allauth.account.models import EmailAddress
from dateutil import parser
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, force_authenticate

from siteapps.socialmedia.models import Media, MediaPost, TextComment
from siteapps.species.models import SpeciesName
from siteapps.users.models import User

# Create your tests here.


class SocialMediaPostAPITestCase(TestCase):
    def setUp(self):
        # Setup a test account
        test_email = "wildebackyard@fakeemail.com"
        test_password = "fakepassword"

        self.user = User.objects.create(email=test_email)
        self.user.set_password(test_password)
        self.user.is_superuser = True
        self.user.save()

        self.client = APIClient()
        self.client.login(email=test_email, password=test_password)

        # Get the auth token from the test account
        login_response = self.client.post(
            "/users/login/", {"email": test_email, "password": test_password}, format="json"
        )

        token = json.loads(login_response.content)["key"]
        headers = self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

        # Request data for social media create API
        SpeciesName.objects.create(name="Acorn Woodpecker", scientific_name="a scientific name")
        self.create_post_data = (
            {
                "postTitle": "This is a new post!",
                "latitude": -1.23,
                "longitude": 4.56,
                "privacySetting": "public",
                "geocodedLocationCountry": "United States",
                "geocodedLocationZipCode": "12345",
                "encounterDatetime": "March 22, 2024 12:38 PM",
                "researchUseAllowed": "true",
                "accuracyMeters": 50,
                "species": "Acorn Woodpecker",
            },
        )

    def test_create_post_no_media(self):
        response = self.client.post("/socialmedia/api/posts/create/", self.create_post_data, format="json")

        self.assertEqual(response.status_code, 201)

        post_obj = MediaPost.objects.filter(created_by=self.user).first()

        # Check the proper fields are populated
        self.assertIsNotNone(post_obj.created_by)

        self.assertEqual(post_obj.geoprivacy, self.create_post_data[0].get("privacySetting"))
        self.assertEqual(post_obj.public_location_latitude, self.create_post_data[0].get("latitude"))
        self.assertEqual(post_obj.public_location_longitude, self.create_post_data[0].get("longitude"))
        self.assertEqual(post_obj.geocoded_location_country, self.create_post_data[0].get("geocodedLocationCountry"))

    def test_get_feed_recent_posts(self):
        # Create a few posts
        for _num in range(0, 23):
            self.client.post("/socialmedia/api/posts/create/", self.create_post_data, format="json")

        response = self.client.post("/socialmedia/api/feed/get/", {}, format="json")

        response = self.client.post("/socialmedia/api/feed/get/?random_arg=12345", {"zipcode": "12345"}, format="json")
        response = self.client.post(
            "/socialmedia/api/feed/get/?random_arg=12345&page=2", {"zipcode": "12345"}, format="json"
        )

    def test_get_comments(self):
        # Create a few posts
        self.client.post("/socialmedia/api/posts/create/", self.create_post_data, format="json")

        self.client.post(
            "/socialmedia/api/comments/create/",
            {"parentPostId": MediaPost.objects.all().first().id, "commentText": "Hello there!"},
            format="json",
        )

        response = self.client.post(
            "/socialmedia/api/posts/responses/get/noauth",
            {"mediaPostId": MediaPost.objects.all().first().id},
            format="json",
        )
        # print(response.content)
