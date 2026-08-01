"""
Fix NULL default_license values and add a DB-level DEFAULT so any
non-ORM insert paths (social auth, admin, raw SQL) also receive 'cc0'
instead of leaving the column NULL and violating the NOT NULL constraint.
"""

from django.db import migrations, models


def backfill_null_licenses(apps, schema_editor):
    """Set any NULL default_license rows to 'cc0'."""
    User = apps.get_model("users", "User")
    User.objects.filter(default_license__isnull=True).update(default_license="cc0")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_user_default_license"),
    ]

    operations = [
        # Step 1: fix any existing NULL rows before tightening the constraint.
        migrations.RunPython(backfill_null_licenses, migrations.RunPython.noop),
        # Step 2: add a DB-level DEFAULT so future non-ORM inserts never produce NULL.
        migrations.AlterField(
            model_name="user",
            name="default_license",
            field=models.CharField(
                choices=[
                    ("cc0", "CC0 — Public Domain Dedication"),
                    ("cc-by", "CC BY — Attribution"),
                    ("cc-by-sa", "CC BY-SA — Attribution-ShareAlike"),
                    ("cc-by-nd", "CC BY-ND — Attribution-NoDerivatives"),
                    ("cc-by-nc", "CC BY-NC — Attribution-NonCommercial"),
                    ("cc-by-nc-sa", "CC BY-NC-SA — Attribution-NonCommercial-ShareAlike"),
                    ("cc-by-nc-nd", "CC BY-NC-ND — Attribution-NonCommercial-NoDerivatives"),
                    ("all-rights-reserved", "All Rights Reserved"),
                ],
                db_default="cc0",
                default="cc0",
                help_text="Default license applied to new sightings and media",
                max_length=32,
            ),
        ),
    ]
