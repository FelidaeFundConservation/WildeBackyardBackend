"""Test-specific settings that use SQLite and don't require external services"""

from .base import *  # noqa

DEBUG = True

# Use pysqlite3 for better spatialite support in tests
import sys
sys.modules['sqlite3'] = __import__('pysqlite3')

# Use SQLite with Spatialite extension for testing GeoDjango
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": ":memory:",
    }
}

# Skip email verification for tests
ACCOUNT_EMAIL_VERIFICATION = "none"

# Email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable Azure Storage for tests
AZURE_STORAGE_ACCOUNT_NAME = "test-account"
AZURE_STORAGE_CONTAINER_NAME = "test-container"

# GCS bucket name for tests (tests use mocks, so this won't access real GCS)
GCS_BUCKET_NAME = "test-wildepod-backyard"
