# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""Tests for App Engine egress configuration used by Mailgun IP allowlisting."""
from pathlib import Path
import unittest

try:
    import yaml
except ImportError:  # pragma: no cover - fallback for minimal environments
    yaml = None


class TestMailgunIPAllowlistConfig(unittest.TestCase):
    """Validate the deployment config required for Mailgun IP allowlisting."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent

    def test_app_yaml_routes_all_traffic_through_vpc_connector(self):
        content = (self.repo_root / "app.yaml").read_text(encoding="utf-8")

        self._assert_vpc_allowlist_config_present(
            content,
            expected_connector_resource=(
                "projects/wildepod-339517/locations/us-west2/connectors/wildepod-connector"
            ),
        )

    def test_staging_yaml_routes_all_traffic_through_vpc_connector(self):
        content = (self.repo_root / "staging.yaml").read_text(encoding="utf-8")

        self._assert_vpc_allowlist_config_present(
            content,
            expected_connector_resource=(
                "projects/wildepod-339517/locations/us-west2/connectors/wildepod-connector"
            ),
        )

    def test_deploy_script_preserves_all_traffic_egress_setting(self):
        content = (self.repo_root / "gcp_deployment" / "scripts" / "deploy_gcp.sh").read_text(encoding="utf-8")

        self.assertIn("vpc_access_connector:", content)
        self.assertIn("egress_setting: all-traffic", content)

    def test_template_documents_all_traffic_egress_setting(self):
        content = (self.repo_root / "gcp_deployment" / "templates" / "TEMPLATE_app_yaml.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("# vpc_access_connector:", content)
        self.assertIn('#   egress_setting: all-traffic', content)

    def _assert_vpc_allowlist_config_present(self, content, expected_connector_resource):
        parsed = self._load_yaml(content)

        self.assertIn("vpc_access_connector", parsed)
        connector_name = parsed["vpc_access_connector"]["name"]
        self.assertEqual(
            connector_name,
            expected_connector_resource,
            f"Expected sanctioned connector '{expected_connector_resource}', got '{connector_name}'",
        )
        self.assertEqual(parsed["vpc_access_connector"]["egress_setting"], "all-traffic")

    def _load_yaml(self, content):
        if yaml is not None:
            return yaml.safe_load(content)

        parsed = {}
        current_key = None

        for raw_line in content.splitlines():
            if not raw_line or raw_line.lstrip().startswith("#"):
                continue

            if not raw_line.startswith(" "):
                key, _, value = raw_line.partition(":")
                key = key.strip()
                value = value.strip()
                if value:
                    parsed[key] = value.strip('"')
                    current_key = None
                else:
                    parsed[key] = {}
                    current_key = key
                continue

            if current_key is None:
                continue

            key, _, value = raw_line.strip().partition(":")
            parsed[current_key][key.strip()] = value.strip().strip('"')

        return parsed


if __name__ == "__main__":
    unittest.main()
