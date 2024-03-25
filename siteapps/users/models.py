import random
import string
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


def generate_random_name():
    random_digits = "".join(random.choices(string.digits, k=6))
    return "Backyarder" + random_digits


# Model to extend django user model to have additional profile fields
class User(AbstractUser, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # User model only needs email and password. No username is needed.
    username = None
    email = models.EmailField("email address", unique=True)

    #: Keep only a name field instead of first & last names
    name = models.CharField("Name", max_length=255, default=generate_random_name)
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    # The user's homebase location
    location_latitude = models.FloatField(null=True)
    location_longitude = models.FloatField(null=True)

    # Zip code if the user doesn't want to give precise location
    zipcode = models.IntegerField(null=True)

    # History of model instance changes
    history = HistoricalRecords()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ("name", "email")
