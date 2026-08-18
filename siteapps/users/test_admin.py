# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Tests for User admin interface
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from siteapps.users.models import BannedEmail

User = get_user_model()


class UserAdminAccessTestCase(TestCase):
    """Test admin access restrictions"""

    def setUp(self):
        self.client = Client()
        # Create a regular user
        self.regular_user = User.objects.create_user(
            email="regular@example.com", password="testpass123", name="RegularUser"
        )
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", name="AdminUser"
        )

    def test_admin_access_requires_superuser(self):
        """Test that only superusers can access admin"""
        # Try to access admin without login
        response = self.client.get("/admin/")
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_admin_access_denied_for_regular_user(self):
        """Test that regular users cannot access admin"""
        self.client.login(email="regular@example.com", password="testpass123")
        response = self.client.get("/admin/")
        # Should redirect to login (regular users don't have access)
        self.assertEqual(response.status_code, 302)

    def test_admin_access_allowed_for_superuser(self):
        """Test that superusers can access admin"""
        self.client.login(email="admin@example.com", password="adminpass123")
        response = self.client.get("/admin/")
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)

    def test_admin_user_list_accessible_for_superuser(self):
        """Test that superusers can access the user list in admin"""
        self.client.login(email="admin@example.com", password="adminpass123")
        # Get the admin changelist URL for users
        url = reverse("admin:users_user_changelist")
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        # Should contain both users
        self.assertContains(response, "regular@example.com")
        self.assertContains(response, "admin@example.com")

    def test_admin_user_detail_accessible_for_superuser(self):
        """Test that superusers can access user detail pages in admin (fixes 500 error)"""
        self.client.login(email="admin@example.com", password="adminpass123")
        # Get the admin change URL for a specific user
        url = reverse("admin:users_user_change", args=[self.regular_user.id])
        response = self.client.get(url)
        # Should return 200 OK (this was causing 500 error before)
        self.assertEqual(response.status_code, 200)
        # Should contain user's email
        self.assertContains(response, "regular@example.com")

    def test_admin_user_add_accessible_for_superuser(self):
        """Test that superusers can access the add user page"""
        self.client.login(email="admin@example.com", password="adminpass123")
        # Get the admin add URL for users
        url = reverse("admin:users_user_add")
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)

    def test_admin_user_detail_shows_staff_and_superuser_fields(self):
        """Test that the user detail page shows is_staff and is_superuser fields"""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:users_user_change", args=[self.regular_user.id])
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        # Should contain the is_staff field
        self.assertContains(response, "is_staff")
        # Should contain the is_superuser field
        self.assertContains(response, "is_superuser")
        # Should contain the Permissions section
        self.assertContains(response, "Permissions")

    def test_admin_user_add_shows_staff_and_superuser_fields(self):
        """Test that the add user page shows is_staff and is_superuser fields"""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:users_user_add")
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        # Should contain the is_staff field
        self.assertContains(response, "is_staff")
        # Should contain the is_superuser field
        self.assertContains(response, "is_superuser")

    def test_admin_user_list_shows_superuser_column(self):
        """Test that the user list shows the is_superuser column"""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:users_user_changelist")
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        # Should contain column header for is_superuser
        self.assertContains(response, "superuser status")


class BannedEmailAdminTestCase(TestCase):
    """Test BannedEmail admin interface"""

    def setUp(self):
        self.client = Client()
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", name="AdminUser"
        )

    def test_admin_bannedemail_list_accessible(self):
        """Test that superusers can access the banned email list in admin"""
        # Create a banned email
        BannedEmail.objects.create(email="banned@example.com", ban_reason="Spam")

        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:users_bannedemail_changelist")
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        # Should contain the banned email
        self.assertContains(response, "banned@example.com")

    def test_admin_bannedemail_detail_accessible(self):
        """Test that superusers can access banned email detail pages"""
        banned_email = BannedEmail.objects.create(
            email="banned@example.com", ban_reason="Spam"
        )

        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:users_bannedemail_change", args=[banned_email.id])
        response = self.client.get(url)
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "banned@example.com")


class AllauthAdminUnregistrationTestCase(TestCase):
    """Test that allauth EmailAddress model is unregistered from admin"""

    def test_emailaddress_not_registered_in_admin(self):
        """Test that allauth's EmailAddress model is not in the admin"""
        from django.contrib import admin
        from allauth.account.models import EmailAddress

        # EmailAddress should not be in the admin registry
        self.assertNotIn(EmailAddress, admin.site._registry)

    def test_user_model_still_registered(self):
        """Test that our custom User model is still registered"""
        from django.contrib import admin

        # User should still be registered
        self.assertIn(User, admin.site._registry)
