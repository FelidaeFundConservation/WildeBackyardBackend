"""Django settings for wildebackyard-api environment"""

import os

import environ

# Initialize environ first, before importing base
env = environ.Env(DEBUG=(bool, False))

# Override to prevent Azure Key Vault lookup in base.py
# Set a dummy file path to trigger env file read path instead of Azure
from pathlib import Path

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
env_file = ROOT_DIR / ".env.gcp_dummy"
# Create a minimal env dict to prevent Azure lookup
os.environ.setdefault("DJANGO_SECRET_KEY", "temp-change-me-in-secret-manager")

from .base import *  # noqa

# HOSTS CONFIG
# ------------------------------------------------------------------------------
# Allow all hosts for App Engine deployments including versioned deployments
# This is safe as App Engine provides its own security layer via IAP and service authentication
# Pattern: {version}-dot-{service}-dot-{project}.{region}.r.appspot.com
# Can be restricted by setting DISABLE_ALLOWED_HOSTS_CHECK=false in environment
if not env.bool("DISABLE_ALLOWED_HOSTS_CHECK", default=True):
    ALLOWED_HOSTS = [".appspot.com", "localhost", "127.0.0.1"]
else:
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

# Cloud SQL connection configuration
DB_CONNECTION_NAME = env.str("CLOUD_SQL_CONNECTION_NAME", default="wildepod-339517:us-west2:wildepoddb")

# Enable Cloud SQL connection
if os.getenv("GAE_APPLICATION", None):
    DATABASES["default"]["HOST"] = f"/cloudsql/{DB_CONNECTION_NAME}"

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
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}
