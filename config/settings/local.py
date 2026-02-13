"""Local env to do something quick, dirty and destructive. Uses a sqlite db to play around
"""

from .base import *  # noqa

# HOSTS CONFIG
# ------------------------------------------------------------------------------
# Local development allows all hosts by default for convenience
# Can be overridden by setting DISABLE_ALLOWED_HOSTS_CHECK=false and specifying HOST_NAME
if not env.bool("DISABLE_ALLOWED_HOSTS_CHECK", default=True):
    ALLOWED_HOSTS = ["127.0.0.1", env.str("HOST_NAME", "localhost")]
else:
    ALLOWED_HOSTS = ["*"]

# DEBUG MODE
# ------------------------------------------------------------------------------
DEBUG = True

# Skip email verification in local dev so the API unit tests work easily
ACCOUNT_EMAIL_VERIFICATION = "none"

# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.local.application"


# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("DB_NAME", "wildebackyard"),
        "USER": env.str("DB_USER", "jnovak"),
        "PASSWORD": env.str("DB_PASSWORD", "Nashorn9450!"),
        "HOST": env.str("DB_HOST", "localhost"),
        "PORT": env.str("DB_PORT", "5432"),
    }
}


# MEDIA
# ------------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = ("storages.backends.azure_storage.AzureStorage",)
MEDIA_URL = ""


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# CORS
# ------------------------------------------------------------------------------
# Allow Web frontend to connect to Backend API
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5005",
    "http://127.0.0.1:5005",
    "http://0.0.0.0:5005",
]
CORS_ALLOW_CREDENTIALS = True

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
