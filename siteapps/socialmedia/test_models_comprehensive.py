"""
Comprehensive tests for SocialMedia models (Media, TextComment, MediaPost, InappropriateContentReport)
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from siteapps.socialmedia.models import InappropriateContentReport, Media, MediaPost, TextComment
from siteapps.species.models import SpeciesName

User = get_user_model()


class MediaModelTestCase(TestCase):
    """Test Media model CRUD operations"""

    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.user.set_password("testpass")
        self.user.save()

    def test_create_media(self):
        """Test creating a media object"""
        media = Media.objects.create(
            is_video=False, file_cloud_path="test/path/image.jpg", content_hash="abc123", uploaded_by=self.user
        )
        self.assertIsNotNone(media.id)
        self.assertEqual(media.file_cloud_path, "test/path/image.jpg")
        self.assertEqual(media.content_hash, "abc123")
        self.assertFalse(media.is_video)

    def test_read_media(self):
        """Test reading media from database"""
        media = Media.objects.create(
            is_video=True, file_cloud_path="test/path/video.mp4", content_hash="def456", uploaded_by=self.user
        )
        fetched = Media.objects.get(id=media.id)
        self.assertEqual(media.id, fetched.id)
        self.assertTrue(fetched.is_video)

    def test_update_media(self):
        """Test updating media"""
        media = Media.objects.create(
            is_video=False, file_cloud_path="test/path/image.jpg", content_hash="abc123", uploaded_by=self.user
        )
        media.file_cloud_path = "test/path/updated.jpg"
        media.save()

        updated = Media.objects.get(id=media.id)
        self.assertEqual(updated.file_cloud_path, "test/path/updated.jpg")

    def test_delete_media(self):
        """Test deleting media"""
        media = Media.objects.create(
            is_video=False, file_cloud_path="test/path/image.jpg", content_hash="abc123", uploaded_by=self.user
        )
        media_id = media.id
        media.delete()
        self.assertFalse(Media.objects.filter(id=media_id).exists())

    def test_media_user_relationship(self):
        """Test that media is linked to uploading user"""
        media = Media.objects.create(
            is_video=False, file_cloud_path="test/path/image.jpg", content_hash="abc123", uploaded_by=self.user
        )
        self.assertEqual(media.uploaded_by, self.user)
        self.assertIn(media, self.user.uploaded_by_user.all())


class TextCommentModelTestCase(TestCase):
    """Test TextComment model CRUD operations"""

    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.user.set_password("testpass")
        self.user.save()

    def test_create_comment(self):
        """Test creating a text comment"""
        comment = TextComment.objects.create(created_by=self.user, text_content="This is a test comment")
        self.assertIsNotNone(comment.id)
        self.assertEqual(comment.text_content, "This is a test comment")
        self.assertEqual(comment.created_by, self.user)

    def test_read_comment(self):
        """Test reading comment from database"""
        comment = TextComment.objects.create(created_by=self.user, text_content="Test comment")
        fetched = TextComment.objects.get(id=comment.id)
        self.assertEqual(comment.id, fetched.id)
        self.assertEqual(fetched.text_content, "Test comment")

    def test_update_comment(self):
        """Test updating comment"""
        comment = TextComment.objects.create(created_by=self.user, text_content="Original text")
        comment.text_content = "Updated text"
        comment.save()

        updated = TextComment.objects.get(id=comment.id)
        self.assertEqual(updated.text_content, "Updated text")

    def test_delete_comment(self):
        """Test deleting comment"""
        comment = TextComment.objects.create(created_by=self.user, text_content="Test comment")
        comment_id = comment.id
        comment.delete()
        self.assertFalse(TextComment.objects.filter(id=comment_id).exists())

    def test_comment_upvotes(self):
        """Test comment upvoting"""
        comment = TextComment.objects.create(created_by=self.user, text_content="Test comment")
        user2 = User.objects.create(email="user2@example.com")
        user2.set_password("pass")
        user2.save()

        comment.upvoted_by.add(user2)
        self.assertEqual(comment.upvoted_by.count(), 1)
        self.assertIn(user2, comment.upvoted_by.all())


class MediaPostModelTestCase(TestCase):
    """Test MediaPost model CRUD operations"""

    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.user.set_password("testpass")
        self.user.save()
        self.species = SpeciesName.objects.create(name="Test Species", scientific_name="Testus speciesus")
        self.media = Media.objects.create(
            is_video=False, file_cloud_path="test/image.jpg", content_hash="hash123", uploaded_by=self.user
        )

    def test_create_media_post(self):
        """Test creating a media post"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Amazing Wildlife Sighting",
            text_content="Saw this beautiful creature!",
            media=self.media,
            species=self.species,
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0522,
            public_location_longitude=-118.2437,
            accuracy_ring_radius_meters=100,
        )
        self.assertIsNotNone(post.id)
        self.assertEqual(post.title, "Amazing Wildlife Sighting")
        self.assertEqual(post.media, self.media)
        self.assertEqual(post.species, self.species)

    def test_read_media_post(self):
        """Test reading media post from database"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Test Post",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )
        fetched = MediaPost.objects.get(id=post.id)
        self.assertEqual(post.id, fetched.id)
        self.assertEqual(fetched.title, "Test Post")

    def test_update_media_post(self):
        """Test updating media post"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Original Title",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )
        post.title = "Updated Title"
        post.text_content = "Updated content"
        post.save()

        updated = MediaPost.objects.get(id=post.id)
        self.assertEqual(updated.title, "Updated Title")
        self.assertEqual(updated.text_content, "Updated content")

    def test_delete_media_post(self):
        """Test deleting media post"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Test Post",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )
        post_id = post.id
        post.delete()
        self.assertFalse(MediaPost.objects.filter(id=post_id).exists())

    def test_media_post_replies(self):
        """Test adding replies to a media post"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Test Post",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )
        reply = TextComment.objects.create(created_by=self.user, text_content="This is a reply")
        post.replies.add(reply)

        self.assertEqual(post.replies.count(), 1)
        self.assertIn(reply, post.replies.all())

    def test_media_post_privacy_settings(self):
        """Test different privacy settings"""
        # Public
        public_post = MediaPost.objects.create(
            created_by=self.user,
            title="Public Post",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )
        self.assertEqual(public_post.geoprivacy, "1")

        # Obscured
        obscured_post = MediaPost.objects.create(
            created_by=self.user,
            title="Obscured Post",
            encounter_datetime=timezone.now(),
            geoprivacy="2",
            true_location_latitude=34.0,
            true_location_longitude=-118.0,
            obfuscation_range_kilometers=10.0,
        )
        self.assertEqual(obscured_post.geoprivacy, "2")

        # Private
        private_post = MediaPost.objects.create(
            created_by=self.user,
            title="Private Post",
            encounter_datetime=timezone.now(),
            geoprivacy="3",
            private_location_latitude=34.0,
            private_location_longitude=-118.0,
        )
        self.assertEqual(private_post.geoprivacy, "3")

    def test_media_post_location_data(self):
        """Test storing location-related data"""
        post = MediaPost.objects.create(
            created_by=self.user,
            title="Location Test",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0522,
            public_location_longitude=-118.2437,
            geocoded_location_locality="Los Angeles",
            geocoded_location_state="California",
            geocoded_location_country="USA",
            geocoded_location_zip_code="90001",
        )
        self.assertEqual(post.geocoded_location_locality, "Los Angeles")
        self.assertEqual(post.geocoded_location_state, "California")
        self.assertEqual(post.geocoded_location_zip_code, "90001")


class InappropriateContentReportModelTestCase(TestCase):
    """Test InappropriateContentReport model CRUD operations"""

    def setUp(self):
        self.reporter = User.objects.create(email="reporter@example.com")
        self.reporter.set_password("testpass")
        self.reporter.save()
        self.reported_user = User.objects.create(email="reported@example.com")
        self.reported_user.set_password("testpass")
        self.reported_user.save()
        self.post = MediaPost.objects.create(
            created_by=self.reported_user,
            title="Test Post",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )

    def test_create_post_report(self):
        """Test creating a report for a post"""
        report = InappropriateContentReport.objects.create(
            reported_by=self.reporter, reported_user=self.reported_user, reported_post=self.post
        )
        self.assertIsNotNone(report.id)
        self.assertEqual(report.reported_post, self.post)
        self.assertEqual(report.reported_by, self.reporter)
        self.assertFalse(report.resolved)

    def test_create_comment_report(self):
        """Test creating a report for a comment"""
        comment = TextComment.objects.create(created_by=self.reported_user, text_content="Inappropriate comment")
        report = InappropriateContentReport.objects.create(
            reported_by=self.reporter, reported_user=self.reported_user, reported_comment=comment
        )
        self.assertIsNotNone(report.id)
        self.assertEqual(report.reported_comment, comment)

    def test_read_report(self):
        """Test reading report from database"""
        report = InappropriateContentReport.objects.create(
            reported_by=self.reporter, reported_user=self.reported_user, reported_post=self.post
        )
        fetched = InappropriateContentReport.objects.get(id=report.id)
        self.assertEqual(report.id, fetched.id)

    def test_update_report(self):
        """Test updating report status"""
        report = InappropriateContentReport.objects.create(
            reported_by=self.reporter, reported_user=self.reported_user, reported_post=self.post
        )
        report.resolved = True
        report.save()

        updated = InappropriateContentReport.objects.get(id=report.id)
        self.assertTrue(updated.resolved)

    def test_delete_report(self):
        """Test deleting a report"""
        report = InappropriateContentReport.objects.create(
            reported_by=self.reporter, reported_user=self.reported_user, reported_post=self.post
        )
        report_id = report.id
        report.delete()
        self.assertFalse(InappropriateContentReport.objects.filter(id=report_id).exists())

    def test_multiple_reports_on_same_content(self):
        """Test that multiple users can report the same content"""
        reporter2 = User.objects.create(email="reporter2@example.com")
        reporter2.set_password("pass")
        reporter2.save()

        report1 = InappropriateContentReport.objects.create(
            reported_by=self.reporter, reported_user=self.reported_user, reported_post=self.post
        )
        report2 = InappropriateContentReport.objects.create(
            reported_by=reporter2, reported_user=self.reported_user, reported_post=self.post
        )

        reports = InappropriateContentReport.objects.filter(reported_post=self.post)
        self.assertEqual(reports.count(), 2)
