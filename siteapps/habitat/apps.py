# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
from django.apps import AppConfig


class HabitatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "siteapps.habitat"
    verbose_name = "Habitat Classification"
