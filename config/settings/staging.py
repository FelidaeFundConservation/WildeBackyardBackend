from .base import *  # noqa

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
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
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
