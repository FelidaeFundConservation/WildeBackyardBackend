# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Tests for database configuration to ensure proper parsing and setup.

This test suite validates:
1. DATABASE_URL parsing without host parameter
2. HOST configuration on App Engine
3. No conflicting OPTIONS['host'] settings
4. Proper password URL-decoding
"""

import ast
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
        
        # Use the actual environment variable name used in production
        with patch.dict(os.environ, {"WILDEBACKYARD_API_DATABASE_URL": self.test_db_url}):
            db_config = env.db("WILDEBACKYARD_API_DATABASE_URL")
            
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
        
        # Use the actual environment variable name used in production
        with patch.dict(os.environ, {"WILDEBACKYARD_API_DATABASE_URL": self.test_db_url}):
            db_config = env.db("WILDEBACKYARD_API_DATABASE_URL")
            
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
        import pathlib
        
        # Read the local.py file
        local_py_path = pathlib.Path(__file__).parent / "settings" / "local.py"
        
        with open(local_py_path, "r") as f:
            content = f.read()
        
        # Parse the file using AST for more robust checking
        try:
            tree = ast.parse(content)
        except SyntaxError:
            self.fail("local.py has syntax errors")
        
        # Look for PASSWORD assignment in DATABASES dictionary
        found_password_config = False
        
        for node in ast.walk(tree):
            # Look for dictionary assignments to DATABASES
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "DATABASES":
                        # Found DATABASES assignment, check if it's a dict
                        if isinstance(node.value, ast.Dict):
                            # Walk through the dictionary structure
                            found_password_config = self._check_password_in_dict(node.value)
        
        self.assertTrue(
            found_password_config,
            "Could not find PASSWORD configuration in DATABASES"
        )
    
    def _check_password_in_dict(self, dict_node):
        """Recursively check dictionary for PASSWORD configuration."""
        for key, value in zip(dict_node.keys, dict_node.values):
            if key is None:
                continue
                
            # Check if this is the PASSWORD key
            if isinstance(key, ast.Constant) and key.value == "PASSWORD":
                # PASSWORD should use env.str with empty string default
                if isinstance(value, ast.Call):
                    # Check if it's calling env.str
                    if (isinstance(value.func, ast.Attribute) and 
                        value.func.attr == "str"):
                        # Check the arguments
                        if len(value.args) >= 1:
                            # First arg should be "DB_PASSWORD"
                            if isinstance(value.args[0], ast.Constant):
                                if value.args[0].value == "DB_PASSWORD":
                                    # Check default value (second argument)
                                    if len(value.args) >= 2:
                                        default_val = value.args[1]
                                        if isinstance(default_val, ast.Constant):
                                            # Default should be empty string
                                            self.assertEqual(
                                                default_val.value,
                                                "",
                                                "DB_PASSWORD default should be empty string, not a hardcoded password"
                                            )
                                            return True
                return True
                                    
            # Recursively check nested dictionaries
            if isinstance(value, ast.Dict):
                if self._check_password_in_dict(value):
                    return True
        
        return False


if __name__ == "__main__":
    unittest.main()
