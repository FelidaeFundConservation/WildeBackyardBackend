# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "siteapps.users"

    def ready(self):
        import siteapps.users.password_reset
