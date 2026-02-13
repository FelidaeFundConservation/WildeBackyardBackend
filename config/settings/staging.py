from .base import *  # noqa

# HOSTS CONFIG
# ------------------------------------------------------------------------------
# Staging allows all hosts to support temporary deployments and testing
# This is safe for staging as it's not production
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
        "HOST": env.str("DB_HOST", SECRETS.get("DB-HOST", "localhost")),
        "USER": env.str("DB_USER", SECRETS.get("DB-USER", "wildepod_staging_user")),
        "PASSWORD": env.str("DB_PASSWORD", SECRETS.get("DB-PASSWORD", "")),
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
