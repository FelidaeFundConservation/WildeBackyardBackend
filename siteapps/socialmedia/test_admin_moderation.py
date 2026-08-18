# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Tests for Django Admin moderation interface
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.utils import timezone

from siteapps.socialmedia.admin import InappropriateContentReportAdmin
from siteapps.socialmedia.models import InappropriateContentReport, MediaPost, TextComment
from siteapps.users.models import BannedEmail

User = get_user_model()


class MockRequest:
    """Mock request object for admin testing"""

    def __init__(self, user):
        self.user = user
        # Django's message framework requires _messages attribute
        # Use FallbackStorage for proper message handling
        self.session = {}
        self._messages = FallbackStorage(self)


class InappropriateContentReportAdminTest(TestCase):
    """Test cases for InappropriateContentReport admin interface"""

    def setUp(self):
        """Set up test data"""
        # Create staff user
        self.staff_user = User.objects.create(
            email="staff@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.staff_user.set_password("password")
        self.staff_user.save()

        # Create regular user
        self.regular_user = User.objects.create(
            email="regular@example.com",
        )
        self.regular_user.set_password("password")
        self.regular_user.save()

        # Create offending user
        self.offending_user = User.objects.create(
            email="offender@example.com",
            warnings=1,
        )

        # Create test post
        self.post = MediaPost.objects.create(
            created_by=self.offending_user,
            title="Test Post",
            text_content="Test content",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )

        # Create test comment
        self.comment = TextComment.objects.create(
            created_by=self.offending_user,
            text_content="Test comment",
        )

        # Create test report
        self.report = InappropriateContentReport.objects.create(
            reported_by=self.regular_user,
            reported_user=self.offending_user,
            reported_post=self.post,
            resolved=False,
        )

        # Set up admin
        self.site = AdminSite()
        self.admin = InappropriateContentReportAdmin(InappropriateContentReport, self.site)
        self.request = MockRequest(self.staff_user)
        self.factory = RequestFactory()

    def test_list_display_fields(self):
        """Test that list_display fields are properly configured"""
        expected_fields = (
            "id",
            "get_content_type",
            "get_content_preview",
            "reported_user_link",
            "reported_by_link",
            "resolved",
            "get_user_warnings",
            "created",
        )
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_get_content_type_post(self):
        """Test get_content_type returns correct value for post"""
        content_type = self.admin.get_content_type(self.report)
        self.assertIn("Post", content_type)

    def test_get_content_type_comment(self):
        """Test get_content_type returns correct value for comment"""
        comment_report = InappropriateContentReport.objects.create(
            reported_by=self.regular_user,
            reported_user=self.offending_user,
            reported_comment=self.comment,
            resolved=False,
        )
        content_type = self.admin.get_content_type(comment_report)
        self.assertIn("Comment", content_type)

    def test_get_content_preview(self):
        """Test get_content_preview returns content preview"""
        preview = self.admin.get_content_preview(self.report)
        self.assertIn("Test Post", preview)
        self.assertIn("Test content", preview)

    def test_get_user_warnings(self):
        """Test get_user_warnings displays warning count"""
        warnings_html = self.admin.get_user_warnings(self.report)
        self.assertIn("1", warnings_html)  # offending_user has 1 warning

    def test_mark_resolved_no_action(self):
        """Test mark_resolved_no_action action"""
        queryset = InappropriateContentReport.objects.filter(id=self.report.id)
        self.admin.mark_resolved_no_action(self.request, queryset)

        # Refresh report from database
        self.report.refresh_from_db()
        self.assertTrue(self.report.resolved)

    def test_issue_warning_and_delete(self):
        """Test issue_warning_and_delete action"""
        initial_warnings = self.offending_user.warnings
        post_id = self.post.id

        queryset = InappropriateContentReport.objects.filter(id=self.report.id)
        self.admin.issue_warning_and_delete(self.request, queryset)

        # Refresh user from database
        self.offending_user.refresh_from_db()

        # Check warning was incremented
        self.assertEqual(self.offending_user.warnings, initial_warnings + 1)

        # Check post was deleted
        self.assertFalse(MediaPost.objects.filter(id=post_id).exists())

        # Check report is resolved
        self.report.refresh_from_db()
        self.assertTrue(self.report.resolved)

    def test_ban_user_and_delete_all_content(self):
        """Test ban_user_and_delete_all_content action"""
        # Create additional content from offending user
        additional_post = MediaPost.objects.create(
            created_by=self.offending_user,
            title="Another Post",
            encounter_datetime=timezone.now(),
            geoprivacy="1",
            public_location_latitude=34.0,
            public_location_longitude=-118.0,
        )
        additional_comment = TextComment.objects.create(
            created_by=self.offending_user,
            text_content="Another comment",
        )

        queryset = InappropriateContentReport.objects.filter(id=self.report.id)
        self.admin.ban_user_and_delete_all_content(self.request, queryset)

        # Check all content was deleted
        self.assertEqual(MediaPost.objects.filter(created_by=self.offending_user).count(), 0)
        self.assertEqual(TextComment.objects.filter(created_by=self.offending_user).count(), 0)

        # Check user email is banned
        self.assertTrue(BannedEmail.objects.filter(email=self.offending_user.email).exists())

        # Check report is resolved
        self.report.refresh_from_db()
        self.assertTrue(self.report.resolved)

    def test_get_user_history(self):
        """Test get_user_history displays moderation history"""
        history_html = self.admin.get_user_history(self.report)
        self.assertIn("Moderation History", history_html)
        # Check for user's name (which is displayed instead of email)
        self.assertIn(self.offending_user.name, history_html)

    def test_readonly_fields(self):
        """Test that sensitive fields are readonly"""
        readonly_fields = self.admin.readonly_fields
        self.assertIn("reported_by", readonly_fields)
        self.assertIn("reported_user", readonly_fields)
        self.assertIn("reported_comment", readonly_fields)
        self.assertIn("reported_post", readonly_fields)

    def test_has_delete_permission_superuser(self):
        """Test superusers can delete reports"""
        self.assertTrue(self.admin.has_delete_permission(self.request, self.report))

    def test_has_delete_permission_staff(self):
        """Test regular staff cannot delete reports"""
        # Create staff user (not superuser)
        staff_user = User.objects.create(email="staff2@example.com", is_staff=True, is_superuser=False)
        staff_request = MockRequest(staff_user)
        self.assertFalse(self.admin.has_delete_permission(staff_request, self.report))

    def test_search_fields(self):
        """Test search fields are properly configured"""
        expected_fields = (
            "reported_user__email",
            "reported_user__name",
            "reported_by__email",
            "reported_by__name",
            "warning_notes",
        )
        self.assertEqual(self.admin.search_fields, expected_fields)

    def test_list_filter(self):
        """Test list filters are properly configured"""
        expected_filters = (
            "resolved",
            "created",
            "modified",
        )
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_ordering(self):
        """Test default ordering (unresolved first, then by created date)"""
        expected_ordering = ("resolved", "-created")
        self.assertEqual(self.admin.ordering, expected_ordering)

    def test_issue_warning_with_custom_notes(self):
        """Test issuing warning with custom warning notes"""
        self.report.warning_notes = "Custom warning message"
        self.report.save()

        queryset = InappropriateContentReport.objects.filter(id=self.report.id)
        self.admin.issue_warning_and_delete(self.request, queryset)

        # Refresh report
        self.report.refresh_from_db()
        self.assertEqual(self.report.warning_notes, "Custom warning message")
        self.assertTrue(self.report.resolved)

    def test_get_content_detail_for_deleted_content(self):
        """Test get_content_detail when content is deleted"""
        # Delete the post
        self.post.delete()
        self.report.reported_post = None
        self.report.save()

        detail_html = self.admin.get_content_detail(self.report)
        # Verify the exact string returned
        self.assertEqual(detail_html, "Content no longer available (may have been deleted)")
