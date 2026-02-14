"""
Tests for database configuration to ensure proper parsing and setup.

This test suite validates:
1. DATABASE_URL parsing without host parameter
2. HOST configuration on App Engine
3. No conflicting OPTIONS['host'] settings
4. Proper password URL-decoding
"""

import os
import unittest
from unittest.mock import patch

import environ


class TestDatabaseConfiguration(unittest.TestCase):
    """Test database configuration for wildebackyard_api settings."""

    def setUp(self):
        """Set up test environment variables."""
        self.test_db_url = (
            "postgres://wildepod_wildebackyard_api_user:"
            "%2FREDACTED%2BP%2BMU%3D"
            "@/wildebackyard_api_staging"
        )
        self.expected_password = "/REDACTED="
        self.cloud_sql_connection = "wildepod-339517:us-west2:wildepoddb"

    def test_database_url_parsing_without_host_param(self):
        """Test that DATABASE_URL without host parameter parses correctly."""
        env = environ.Env()
        
        with patch.dict(os.environ, {"TEST_DB_URL": self.test_db_url}):
            db_config = env.db("TEST_DB_URL")
            
            # Verify basic configuration
            self.assertEqual(db_config["ENGINE"], "django.db.backends.postgresql")
            self.assertEqual(db_config["NAME"], "wildebackyard_api_staging")
            self.assertEqual(db_config["USER"], "wildepod_wildebackyard_api_user")
            
            # HOST should be empty when no host in URL
            self.assertEqual(db_config.get("HOST", ""), "")
            
            # OPTIONS should not contain 'host'
            options = db_config.get("OPTIONS", {})
            self.assertNotIn("host", options, "OPTIONS should not contain 'host' key")

    def test_password_url_decoding(self):
        """Test that the password is correctly URL-decoded."""
        env = environ.Env()
        
        with patch.dict(os.environ, {"TEST_DB_URL": self.test_db_url}):
            db_config = env.db("TEST_DB_URL")
            
            # Password should be URL-decoded
            self.assertEqual(
                db_config["PASSWORD"],
                self.expected_password,
                "Password should be URL-decoded from %2F to / and %2B to +"
            )

    def test_host_configuration_on_app_engine(self):
        """Test that HOST is correctly set when running on App Engine."""
        env = environ.Env()
        
        test_env = {
            "WILDEBACKYARD_API_DATABASE_URL": self.test_db_url,
            "CLOUD_SQL_CONNECTION_NAME": self.cloud_sql_connection,
            "GAE_APPLICATION": "wildepod-339517"
        }
        
        with patch.dict(os.environ, test_env):
            # Simulate what wildebackyard_api.py does
            DATABASES = {"default": env.db("WILDEBACKYARD_API_DATABASE_URL")}
            DB_CONNECTION_NAME = env.str("CLOUD_SQL_CONNECTION_NAME")
            
            if os.getenv("GAE_APPLICATION", None):
                DATABASES["default"]["HOST"] = f"/cloudsql/{DB_CONNECTION_NAME}"
                # Remove any host setting from OPTIONS to avoid conflicts
                if "OPTIONS" in DATABASES["default"] and "host" in DATABASES["default"]["OPTIONS"]:
                    del DATABASES["default"]["OPTIONS"]["host"]
            
            # Verify HOST is set correctly
            expected_host = f"/cloudsql/{self.cloud_sql_connection}"
            self.assertEqual(DATABASES["default"]["HOST"], expected_host)
            
            # Verify no OPTIONS['host'] conflict
            options = DATABASES["default"].get("OPTIONS", {})
            self.assertNotIn("host", options, "OPTIONS['host'] should be removed to avoid conflicts")

    def test_no_gae_application_env(self):
        """Test that HOST remains empty when not on App Engine."""
        env = environ.Env()
        
        test_env = {
            "WILDEBACKYARD_API_DATABASE_URL": self.test_db_url,
            "CLOUD_SQL_CONNECTION_NAME": self.cloud_sql_connection
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            DATABASES = {"default": env.db("WILDEBACKYARD_API_DATABASE_URL")}
            
            # Don't set HOST if not on App Engine
            if os.getenv("GAE_APPLICATION", None):
                DATABASES["default"]["HOST"] = f"/cloudsql/{os.environ['CLOUD_SQL_CONNECTION_NAME']}"
            
            # HOST should remain empty
            self.assertEqual(DATABASES["default"].get("HOST", ""), "")

    def test_old_url_format_with_host_param(self):
        """Test that old URL format with host parameter in query string causes OPTIONS conflict."""
        # This test documents the bug that was fixed
        old_url = (
            "postgres://wildepod_wildebackyard_api_user:"
            "%2FREDACTED%2BP%2BMU%3D"
            "@/wildebackyard_api_staging"
            "?host=/cloudsql/wildepod-339517:us-west2:wildepoddb"
        )
        
        env = environ.Env()
        
        with patch.dict(os.environ, {"OLD_DB_URL": old_url}):
            db_config = env.db("OLD_DB_URL")
            
            # With the old format, OPTIONS['host'] would be set
            options = db_config.get("OPTIONS", {})
            self.assertIn("host", options, "Old URL format puts host in OPTIONS")
            self.assertEqual(
                options["host"],
                "/cloudsql/wildepod-339517:us-west2:wildepoddb"
            )


class TestLocalDatabaseConfiguration(unittest.TestCase):
    """Test local database configuration doesn't expose credentials."""

    def test_local_settings_no_hardcoded_password(self):
        """Test that local.py doesn't contain hardcoded passwords."""
        # Read the local.py file
        import pathlib
        local_py_path = pathlib.Path(__file__).parent / "settings" / "local.py"
        
        with open(local_py_path, "r") as f:
            content = f.read()
        
        # Check that password uses env.str, not a hardcoded value
        # The pattern should be: env.str("DB_PASSWORD", "")
        # NOT: env.str("DB_PASSWORD", "some_password")
        
        self.assertIn('env.str("DB_PASSWORD"', content, "local.py should use env.str for password")
        
        # Make sure there's no obvious password in the default
        # This is a simple check - just make sure the default is empty string
        import re
        password_pattern = r'env\.str\(["\']DB_PASSWORD["\'],\s*["\']([^"\']*)["\']'
        matches = re.findall(password_pattern, content)
        
        if matches:
            for match in matches:
                # The default should be empty string
                self.assertEqual(
                    match,
                    "",
                    "DB_PASSWORD default should be empty string, not a hardcoded password"
                )


if __name__ == "__main__":
    unittest.main()
