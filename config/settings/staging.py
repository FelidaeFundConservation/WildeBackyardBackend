from .base import *  # noqa
from urllib.parse import quote

from google.cloud import secretmanager


def _get_staging_db_url_from_secret() -> str:
    """Build a Cloud SQL PostgreSQL URL from a Secret Manager password value."""
    secret_id = env.str("STAGING_DB_PASSWORD_SECRET_ID", default="")
    if not secret_id:
        return ""

    project_id = env.str("GOOGLE_CLOUD_PROJECT", default=env.str("GCP_PROJECT", default=""))
    if not project_id:
        raise RuntimeError("STAGING_DB_PASSWORD_SECRET_ID is set but project id is missing.")

    secret_version = env.str("STAGING_DB_PASSWORD_SECRET_VERSION", default="latest")
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/{secret_version}"

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_name})
    password = response.payload.data.decode("utf-8").strip()

    db_user = env.str("CLOUD_SQL_DATABASE_USER_STAGING", default="wildepod_wildebackyard_api_user")
    db_name = env.str("CLOUD_SQL_DATABASE_NAME_STAGING", default="wildebackyard_api_staging")
    encoded_password = quote(password, safe="")
    return f"postgres://{db_user}:{encoded_password}@/{db_name}"

# HOSTS CONFIG
# ------------------------------------------------------------------------------
# Staging allows all hosts by default to support temporary deployments and versioned URLs
# This is appropriate for staging as it's behind App Engine security and not user-facing
# Always allow all hosts for staging to prevent "disallowed host" errors with versioned URLs
ALLOWED_HOSTS = ["*"]


# DEBUG MODE
# ------------------------------------------------------------------------------
DEBUG = True

# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.staging.application"


# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
# Use PostgreSQL for GCP Cloud SQL deployment
# For GCP deployment, use CLOUD_SQL_DATABASE_URL_STAGING environment variable
# For local development, use individual DB_* environment variables
staging_db_url = env.str("CLOUD_SQL_DATABASE_URL_STAGING", default="")
if not staging_db_url:
    staging_db_url = _get_staging_db_url_from_secret()

if staging_db_url:
    DATABASES = {"default": env.db_url_config(staging_db_url)}

    # Cloud SQL connection configuration
    DB_CONNECTION_NAME = env.str("CLOUD_SQL_CONNECTION_NAME", default="wildepod-339517:us-west2:wildepoddb")

    # Enable Cloud SQL connection when deployed to App Engine
    if os.getenv("GAE_APPLICATION", None):
        DATABASES["default"]["HOST"] = f"/cloudsql/{DB_CONNECTION_NAME}"
        # Remove any host setting from OPTIONS to avoid conflicts with HOST
        # (django-environ may have parsed it from DATABASE_URL query string)
        if "OPTIONS" in DATABASES["default"] and "host" in DATABASES["default"]["OPTIONS"]:
            del DATABASES["default"]["OPTIONS"]["host"]
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env.str("DB_NAME_STAGING", "wildepod_staging"),
            "HOST": env.str("DB_HOST", "localhost"),
            "USER": env.str("DB_USER", "wildepod_staging_user"),
            "PASSWORD": env.str("DB_PASSWORD", ""),
            "PORT": env.int("DB_PORT", 5432),
        }
    }


# MEDIA
# ------------------------------------------------------------------------------
# Media files are uploaded directly to GCS via google.cloud.storage client
# See siteapps/socialmedia/views.py for GCS upload implementation


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}


# CUSTOM VARIABLES
# ------------------------------------------------------------------------------
