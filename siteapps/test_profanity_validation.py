"""
Tests for profanity validation across models and API views.
"""

import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from django.utils import timezone

from django.contrib.auth import get_user_model
from siteapps.socialmedia.models import MediaPost, TextComment
from siteapps.validators import validate_no_profanity

User = get_user_model()

CLEAN_TEXT = "I saw a beautiful deer in my backyard"
PROFANE_TEXT = "fuck this shit"


class ValidateNoProfanityTestCase(TestCase):
    """Tests for the validate_no_profanity validator function."""

    def test_clean_text_passes(self):
        """Clean text should not raise ValidationError."""
        try:
            validate_no_profanity(CLEAN_TEXT)
        except ValidationError:
            self.fail("validate_no_profanity raised ValidationError for clean text")

    def test_profane_text_raises(self):
        """Profane text should raise ValidationError."""
        with self.assertRaises(ValidationError):
            validate_no_profanity(PROFANE_TEXT)

    def test_none_passes(self):
        """None value should not raise ValidationError (field may be optional)."""
        try:
            validate_no_profanity(None)
        except ValidationError:
            self.fail("validate_no_profanity raised ValidationError for None")

    def test_empty_string_passes(self):
        """Empty string should not raise ValidationError."""
        try:
            validate_no_profanity("")
        except ValidationError:
            self.fail("validate_no_profanity raised ValidationError for empty string")


class UserNameProfanityModelTestCase(TestCase):
    """Tests that profanity validator is applied to User.name and User.bio model fields."""

    def test_user_name_validator_clean(self):
        """User.name field validator should pass for clean text."""
        user = User(email="test@example.com", name=CLEAN_TEXT)
        try:
            user.full_clean()
        except ValidationError as e:
            if "name" in e.message_dict:
                self.fail("full_clean raised ValidationError on clean user name")

    def test_user_name_validator_profane(self):
        """User.name field validator should raise ValidationError for profane text."""
        user = User(email="test@example.com", name=PROFANE_TEXT)
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn("name", ctx.exception.message_dict)

    def test_user_bio_validator_profane(self):
        """User.bio field validator should raise ValidationError for profane text."""
        user = User(email="test@example.com", bio=PROFANE_TEXT)
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn("bio", ctx.exception.message_dict)


class TextCommentProfanityModelTestCase(TestCase):
    """Tests that profanity validator is applied to TextComment.text_content field."""

    def setUp(self):
        self.user = User.objects.create(email="commenter@example.com")

    def test_comment_text_validator_profane(self):
        """TextComment.text_content field validator should raise ValidationError for profane text."""
        comment = TextComment(created_by=self.user, text_content=PROFANE_TEXT)
        with self.assertRaises(ValidationError) as ctx:
            comment.full_clean()
        self.assertIn("text_content", ctx.exception.message_dict)

    def test_comment_text_validator_clean(self):
        """TextComment.text_content field validator should pass for clean text."""
        comment = TextComment(created_by=self.user, text_content=CLEAN_TEXT)
        try:
            comment.full_clean()
        except ValidationError as e:
            if "text_content" in e.message_dict:
                self.fail("full_clean raised ValidationError on clean comment text")


class MediaPostProfanityModelTestCase(TestCase):
    """Tests that profanity validator is applied to MediaPost.title field."""

    def setUp(self):
        self.user = User.objects.create(email="poster@example.com")

    def test_post_title_validator_profane(self):
        """MediaPost.title field validator should raise ValidationError for profane text."""
        post = MediaPost(
            created_by=self.user,
            title=PROFANE_TEXT,
            encounter_datetime=timezone.now(),
            geoprivacy="1",
        )
        with self.assertRaises(ValidationError) as ctx:
            post.full_clean()
        self.assertIn("title", ctx.exception.message_dict)

    def test_post_title_validator_clean(self):
        """MediaPost.title field validator should pass for clean text."""
        post = MediaPost(
            created_by=self.user,
            title=CLEAN_TEXT,
            encounter_datetime=timezone.now(),
            geoprivacy="1",
        )
        try:
            post.full_clean()
        except ValidationError as e:
            if "title" in e.message_dict:
                self.fail("full_clean raised ValidationError on clean post title")


class ChangeUsernameProfanityAPITestCase(TestCase):
    """Tests that the change_username API endpoint rejects profane usernames."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(email="user@example.com", name="CleanName")
        self.user.set_password("testpassword")
        self.user.save()
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_change_username_profane_rejected(self):
        """API should return 400 when trying to set a profane username."""
        response = self.client.post(
            "/v1/users/profile/change_username",
            data=json.dumps({"newUsername": PROFANE_TEXT}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_change_username_clean_accepted(self):
        """API should accept a clean username."""
        response = self.client.post(
            "/v1/users/profile/change_username",
            data=json.dumps({"newUsername": "NiceNewName"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
