import secrets
import string
import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from siteapps.validators import validate_no_profanity


def generate_random_name():
    random_digits = "".join(secrets.choice(string.digits) for _ in range(6))
    return "Backyarder" + random_digits


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# Model to extend django user model to have additional profile fields
class User(AbstractUser, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # User model only needs email and password. No username is needed.
    username = None
    email = models.EmailField("email address", unique=True)

    #: Keep only a name field instead of first & last names
    name = models.CharField("Name", max_length=255, default=generate_random_name, validators=[validate_no_profanity])
    bio = models.CharField("Bio", max_length=10000, default="", validators=[validate_no_profanity])
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    # The number of warnings the user has received
    warnings = models.IntegerField(default=0)

    # History of model instance changes
    history = HistoricalRecords()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ("name", "email")


# Track emails so users can't delete/recreate account to circumvent comment/media bans
class BannedEmail(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField("email address", unique=True)
    ban_reason = models.CharField(max_length=800, default="")
