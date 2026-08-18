# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Tests for Google Cloud Platform logging configuration.

This test suite validates:
1. google-cloud-logging module import
2. RequestMiddleware is properly included
3. Logging configuration is properly set up
"""

import unittest
from unittest.mock import Mock, patch


class TestGCPLoggingConfiguration(unittest.TestCase):
    """Test GCP logging configuration for wildebackyard_api settings."""

    def test_google_cloud_logging_import(self):
        """Test that google.cloud.logging can be imported."""
        try:
            import google.cloud.logging as gcp_logging  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed to import google.cloud.logging: {e}")

    def test_request_middleware_import(self):
        """Test that RequestMiddleware can be imported."""
        try:
            from google.cloud.logging_v2.handlers.middleware.request import RequestMiddleware  # noqa: F401
        except ImportError as e:
            self.fail(f"Failed to import RequestMiddleware: {e}")

    @patch('google.cloud.logging.Client')
    def test_gcp_logging_configuration_in_settings(self, mock_client):
        """Test that GCP logging is configured in wildebackyard_api settings."""
        # Mock the Client to avoid actual GCP connection
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        # Set up environment variables required for settings
        with patch.dict('os.environ', {
            'WILDEBACKYARD_API_DATABASE_URL': 'postgres://test:test@localhost/test',
            'DJANGO_SECRET_KEY': 'test-key',
        }):
            try:
                # Import the settings module
                from config.settings import wildebackyard_api as settings
                
                # Verify that the Client was instantiated
                self.assertTrue(mock_client.called, "GCP Logging Client should be instantiated")
                
                # Verify setup_logging was called
                mock_client_instance.setup_logging.assert_called_once()
                
            except Exception as e:
                self.fail(f"Failed to load wildebackyard_api settings: {e}")

    @patch('google.cloud.logging.Client')
    def test_request_middleware_in_middleware_list(self, mock_client):
        """Test that RequestMiddleware is included in MIDDLEWARE setting."""
        # Mock the Client to avoid actual GCP connection
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        # Set up environment variables required for settings
        with patch.dict('os.environ', {
            'WILDEBACKYARD_API_DATABASE_URL': 'postgres://test:test@localhost/test',
            'DJANGO_SECRET_KEY': 'test-key',
        }):
            try:
                # Import the settings module
                from config.settings import wildebackyard_api as settings
                
                # Check if RequestMiddleware is in MIDDLEWARE
                middleware_list = getattr(settings, 'MIDDLEWARE', [])
                self.assertIn(
                    'google.cloud.logging_v2.handlers.middleware.request.RequestMiddleware',
                    middleware_list,
                    "RequestMiddleware should be in MIDDLEWARE list"
                )
                
                # Verify it's at the end (last position)
                self.assertEqual(
                    middleware_list[-1],
                    'google.cloud.logging_v2.handlers.middleware.request.RequestMiddleware',
                    "RequestMiddleware should be the last middleware"
                )
                
            except Exception as e:
                self.fail(f"Failed to load wildebackyard_api settings: {e}")

    def test_logging_config_exists(self):
        """Test that LOGGING configuration exists in wildebackyard_api settings."""
        with patch('google.cloud.logging.Client'):
            with patch.dict('os.environ', {
                'WILDEBACKYARD_API_DATABASE_URL': 'postgres://test:test@localhost/test',
                'DJANGO_SECRET_KEY': 'test-key',
            }):
                try:
                    from config.settings import wildebackyard_api as settings
                    
                    # Verify LOGGING configuration exists
                    self.assertTrue(hasattr(settings, 'LOGGING'), "LOGGING configuration should exist")
                    
                    logging_config = getattr(settings, 'LOGGING', {})
                    
                    # Verify basic structure
                    self.assertIn('version', logging_config, "LOGGING should have version")
                    self.assertEqual(logging_config['version'], 1, "LOGGING version should be 1")
                    
                    self.assertIn('disable_existing_loggers', logging_config)
                    self.assertFalse(
                        logging_config['disable_existing_loggers'],
                        "disable_existing_loggers should be False"
                    )
                    
                except Exception as e:
                    self.fail(f"Failed to load wildebackyard_api settings: {e}")


if __name__ == "__main__":
    unittest.main()
