from .base import *  # noqa

# HOSTS CONFIG
# ------------------------------------------------------------------------------
# NOTE: SECURITY WARNING: App Engine's security features ensure that it is safe to
# have ALLOWED_HOSTS = ['*'] when the app is deployed. If you deploy a Django
# app not on App Engine, make sure to set an appropriate host here.
ALLOWED_HOSTS = ["127.0.0.1", env.str("WEBSITE_HOSTNAME", SECRETS.get("HOST-NAME"))]


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
        "PORT": env.str("DB_PORT", "5432"),
    }
}


# MEDIA
# ------------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
AZURE_STORAGE_CONTAINER_NAME = env.str(
    "AZURE_STORAGE_CONTAINER_NAME_STAGING", default=SECRETS.get("AZURE-STORAGE-CONTAINER-NAME-STAGING", None)
)


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
