# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from siteapps.users.adapters import AccountAdapter


class AccountAdapterTests(SimpleTestCase):
    @override_settings(WEB_APP_URL="https://wildebackyard.com")
    def test_email_confirmation_url_points_to_web_verify_endpoint(self):
        adapter = AccountAdapter()
        emailconfirmation = SimpleNamespace(key="abc123")

        result = adapter.get_email_confirmation_url(request=None, emailconfirmation=emailconfirmation)

        self.assertEqual(result, "https://wildebackyard.com/users/verify-email/abc123/")
