"""Test-specific settings that use SQLite and don't require external services"""

from .base import *  # noqa

DEBUG = True

# Use SQLite for testing to avoid database setup
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
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
