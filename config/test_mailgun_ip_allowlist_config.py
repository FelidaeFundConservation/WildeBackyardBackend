# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""Tests for App Engine egress configuration used by Mailgun IP allowlisting."""
from pathlib import Path
import unittest


class TestMailgunIPAllowlistConfig(unittest.TestCase):
    """Validate the deployment config required for Mailgun IP allowlisting."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent

    def test_app_yaml_routes_all_traffic_through_vpc_connector(self):
        content = (self.repo_root / "app.yaml").read_text()

        self._assert_vpc_allowlist_config_present(content)

    def test_staging_yaml_routes_all_traffic_through_vpc_connector(self):
        content = (self.repo_root / "staging.yaml").read_text()

        self._assert_vpc_allowlist_config_present(content)

    def test_deploy_script_preserves_all_traffic_egress_setting(self):
        content = (self.repo_root / "gcp_deployment" / "scripts" / "deploy_gcp.sh").read_text()

        self.assertIn("vpc_access_connector:", content)
        self.assertIn("egress_setting: all-traffic", content)

    def test_template_documents_all_traffic_egress_setting(self):
        content = (self.repo_root / "gcp_deployment" / "templates" / "TEMPLATE_app_yaml.yaml").read_text()

        self.assertIn("# vpc_access_connector:", content)
        self.assertIn('#   egress_setting: all-traffic', content)

    def _assert_vpc_allowlist_config_present(self, content):
        self.assertIn("vpc_access_connector:", content)
        self.assertRegex(
            content,
            r"name:\s+projects/[^\s]+/locations/[^\s]+/connectors/[^\s]+",
        )
        self.assertIn("egress_setting: all-traffic", content)


if __name__ == "__main__":
    unittest.main()
