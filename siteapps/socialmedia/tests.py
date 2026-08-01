import json

from allauth.account.models import EmailAddress
from dateutil import parser
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, force_authenticate

from siteapps.socialmedia.models import BulkUploadSession, InappropriateContentReport, Media, MediaPost, TextComment
from siteapps.species.models import SpeciesName
from siteapps.users.models import BannedEmail, User

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
            "/v1/users/login/", {"email": test_email, "password": test_password}, format="json"
        )

        token = json.loads(login_response.content)["key"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

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
                "accuracyMeters": 50,
                "species": "Acorn Woodpecker",
            },
        )

    # test_create_post_no_media removed - covered in test_api_comprehensive.py

    def test_get_feed_recent_posts(self):
        # Create a few posts
        for _num in range(0, 23):
            self.client.post("/v1/socialmedia/api/posts/create/", self.create_post_data, format="json")

        self.client.post("/v1/socialmedia/api/feed/get/", {}, format="json")

        response = self.client.post(
            "/v1/socialmedia/api/feed/get/?random_arg=12345", {"zipCode": "12345"}, format="json"
        )

        response = self.client.post(
            "/v1/socialmedia/api/feed/get/?random_arg=12345&offset=10", {"zipCode": "12345"}, format="json"
        )

        self.assertEqual(response.status_code, 200)

    def test_get_comments(self):
        # Create a few posts
        self.client.post("/v1/socialmedia/api/posts/create/", self.create_post_data, format="json")

        self.client.post(
            "/v1/socialmedia/api/comments/create/",
            {"parentPostId": MediaPost.objects.all().first().id, "commentText": "Hello there!"},
            format="json",
        )

        self.client.post(
            "/v1/socialmedia/api/posts/responses/get/noauth",
            {"mediaPostId": MediaPost.objects.all().first().id},
            format="json",
        )

    # test_get_comments_with_pagination removed - covered in test_api_comprehensive.py

    def test_report_posts(self):
        # Create a post
        self.client.post("/v1/socialmedia/api/posts/create/", self.create_post_data, format="json")

        self.client.post(
            "/v1/socialmedia/api/comments/create/",
            {"parentPostId": MediaPost.objects.all().first().id, "commentText": "Hello there!"},
            format="json",
        )

        response = self.client.post(
            "/v1/socialmedia/api/posts/reports/create",
            {"contentId": MediaPost.objects.all().first().id, "contentType": "MediaPost"},
            format="json",
        )

        self.user.is_staff = True
        self.user.save()

        response = self.client.post(
            "/v1/socialmedia/api/posts/reports/create",
            {"contentId": TextComment.objects.all().first().id, "contentType": "TextComment"},
            format="json",
        )

        response = self.client.get(
            "/v1/socialmedia/api/posts/reports/review",
            format="json",
        )

        response = self.client.post(
            "/v1/socialmedia/api/posts/reports/ban",
            {"reportId": json.loads(response.content)["report_id"], "banReason": "Did a bad thing."},
            format="json",
        )

        response = self.client.get(
            "/v1/socialmedia/api/posts/reports/review",
        )

    # test_banned_user_create_media_post removed - covered in test_api_comprehensive.py

    def test_staff_review_reports(self):
        self.user.is_staff = True
        self.user.save()

        self.client.post("/v1/socialmedia/api/posts/create/", self.create_post_data, format="json")

        InappropriateContentReport.objects.create(reported_post=MediaPost.objects.all().first())

        self.client.get("/v1/socialmedia/api/posts/reports/review", format="json")

    # test_edit_post removed - covered in test_api_comprehensive.py


class BulkUploadSessionDeleteAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="bulk-delete@test.com")
        self.user.set_password("password123")
        self.user.save()

        token, _created = Token.objects.get_or_create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _create_post(self, title: str) -> MediaPost:
        return MediaPost.objects.create(
            created_by=self.user,
            title=title,
            encounter_datetime=timezone.now(),
            geoprivacy=settings.PRIVACY_SETTING_PUBLIC,
        )

    def test_delete_bulk_upload_removes_unique_associated_posts(self):
        post = self._create_post("Unique post")
        session = BulkUploadSession.objects.create(
            user=self.user,
            name="Session A",
            image_count=1,
            post_ids=[str(post.id)],
        )

        response = self.client.delete(f"/v1/socialmedia/api/bulk-upload/{session.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("deleted_post_count"), 1)
        self.assertEqual(response.json().get("retained_shared_post_count"), 0)
        self.assertFalse(BulkUploadSession.objects.filter(id=session.id).exists())
        self.assertFalse(MediaPost.objects.filter(id=post.id).exists())

    def test_delete_bulk_upload_keeps_posts_shared_with_other_sessions(self):
        post = self._create_post("Shared post")
        session_one = BulkUploadSession.objects.create(
            user=self.user,
            name="Session One",
            image_count=1,
            post_ids=[str(post.id)],
        )
        BulkUploadSession.objects.create(
            user=self.user,
            name="Session Two",
            image_count=1,
            post_ids=[str(post.id)],
        )

        response = self.client.delete(f"/v1/socialmedia/api/bulk-upload/{session_one.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("deleted_post_count"), 0)
        self.assertEqual(response.json().get("retained_shared_post_count"), 1)
        self.assertFalse(BulkUploadSession.objects.filter(id=session_one.id).exists())
        self.assertTrue(MediaPost.objects.filter(id=post.id).exists())
