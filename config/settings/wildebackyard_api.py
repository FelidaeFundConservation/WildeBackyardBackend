"""Django settings for wildebackyard-api environment"""

import os
from pathlib import Path

import environ

# Initialize environ first, before importing base
env = environ.Env(DEBUG=(bool, False))

# Override to prevent Azure Key Vault lookup in base.py
# Set a dummy file path to trigger env file read path instead of Azure

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
env_file = ROOT_DIR / ".env.gcp_dummy"
# Create a minimal env dict to prevent Azure lookup
os.environ.setdefault("DJANGO_SECRET_KEY", "temp-change-me-in-secret-manager")

# Import Google Cloud Logging
import google.cloud.logging as gcp_logging

from .base import *  # noqa

# HOSTS CONFIG
# ------------------------------------------------------------------------------
# Allow all hosts for App Engine deployments including versioned deployments
# This is safe as App Engine provides its own security layer via IAP and service authentication
# Pattern: {version}-dot-{service}-dot-{project}.{region}.r.appspot.com
# Always allow all hosts for staging to prevent "disallowed host" errors with versioned URLs
ALLOWED_HOSTS = ["*"]

# DEBUG MODE
# ------------------------------------------------------------------------------
DEBUG = True

# SECURITY
# ------------------------------------------------------------------------------
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="temp-insecure-key-for-initial-deployment")

# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.wildebackyard_api.application"

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("WILDEBACKYARD_API_DATABASE_URL")}

# Override ENGINE to use PostGIS
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# Cloud SQL connection configuration
DB_CONNECTION_NAME = env.str("CLOUD_SQL_CONNECTION_NAME", default="wildepod-339517:us-west2:wildepoddb")

# Enable Cloud SQL connection when in production (GAE_APPLICATION or GAE_ENV for flex)
# Always use Cloud SQL socket for this settings file since it's for GCP deployment
if os.getenv("GAE_APPLICATION", None) or os.getenv("GAE_ENV", None) or os.getenv("PYTHON_ENV") == "production":
    DATABASES["default"]["HOST"] = f"/cloudsql/{DB_CONNECTION_NAME}"
    # Remove any host setting from OPTIONS to avoid conflicts with HOST
    # (django-environ may have parsed it from DATABASE_URL query string)
    if "OPTIONS" in DATABASES["default"] and "host" in DATABASES["default"]["OPTIONS"]:
        del DATABASES["default"]["OPTIONS"]["host"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = False

# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = False

# STORAGES
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/backends/gcloud.html
GS_BUCKET_NAME = "wildepod-339517-wildebackyard-api-media"
GS_DEFAULT_ACL = "publicRead"
GS_FILE_OVERWRITE = False
GS_LOCATION = "media"

# Use GCS for media files
DEFAULT_FILE_STORAGE = "siteapps.my_utils.storages.MediaStorage"

# STATIC
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ADMIN
# ------------------------------------------------------------------------------
ADMIN_URL = "admin/"

# EMAIL
# ------------------------------------------------------------------------------
# Use console backend for staging to avoid email errors
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ALLAUTH
# ------------------------------------------------------------------------------
# Disable email verification for staging
ACCOUNT_EMAIL_VERIFICATION = "optional"

# LOGGING
# ------------------------------------------------------------------------------
# Configure Google Cloud Logging with structlog
import logging

import structlog

# Initialize Google Cloud Logging client
gcp_logging_client = gcp_logging.Client()
gcp_logging_client.setup_logging(log_level=logging.INFO)

# Configure structlog to work with Google Cloud Logging
# This ensures extra dict parameters are properly captured as structured JSON
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Use JSONRenderer to ensure structured output
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Django's LOGGING configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"},
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# MIDDLEWARE
# ------------------------------------------------------------------------------
# Add Google Cloud Logging RequestMiddleware to track requests
MIDDLEWARE = MIDDLEWARE + [
    "google.cloud.logging_v2.handlers.middleware.request.RequestMiddleware",
]
