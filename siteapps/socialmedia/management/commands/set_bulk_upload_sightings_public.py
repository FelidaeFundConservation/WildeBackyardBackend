# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Management command: set_bulk_upload_sightings_public

Reads the WildeBackyardWeb SQLite database to get every post ID that
belongs to a BulkUpload, then directly updates those MediaPost records
in the backend DB:
  - geoprivacy → "public"
  - public_location_latitude / public_location_longitude populated from
    true_location_spatial (the stored exact coordinates)

Usage (from WildeBackyardBackend project root):
    uv run python manage.py set_bulk_upload_sightings_public \
        --settings=config.settings.local [--dry-run]
"""

import sqlite3
import uuid

from django.core.management.base import BaseCommand
from django.conf import settings

# ---------------------------------------------------------------------------
# Path to the web frontend's local SQLite database.
# Adjust if the web app moves its DB elsewhere.
# ---------------------------------------------------------------------------
WEB_SQLITE_PATH = "/home/jnovak/Projects/WildeBackyardWeb/config/db.sqlite3"


def _get_bulk_upload_post_ids():
    """Return a set of UUIDs for every backend_post_id in BulkUploadSighting."""
    conn = sqlite3.connect(WEB_SQLITE_PATH)
    try:
        cur = conn.execute("SELECT backend_post_id FROM sightings_bulkuploadsighting")
        return {uuid.UUID(str(row[0])) for row in cur.fetchall()}
    finally:
        conn.close()


class Command(BaseCommand):
    help = (
        "Set geoprivacy=public for all MediaPost records that belong to a "
        "BulkUpload (reads post IDs from the WildeBackyardWeb SQLite DB)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would be changed without writing to the database.",
        )

    def handle(self, *args, **options):
        # Import here so Django is fully set up before we touch the ORM.
        from siteapps.socialmedia.models import MediaPost

        dry_run = options["dry_run"]

        self.stdout.write(f"Reading bulk upload post IDs from: {WEB_SQLITE_PATH}")
        try:
            post_ids = _get_bulk_upload_post_ids()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read web SQLite DB: {e}"))
            return

        self.stdout.write(f"Found {len(post_ids)} bulk-upload post ID(s).")
        if not post_ids:
            self.stdout.write("Nothing to do.")
            return

        posts = MediaPost.objects.filter(id__in=post_ids)
        found = posts.count()
        self.stdout.write(f"Matched {found} MediaPost record(s) in the backend DB.")

        already_public = posts.filter(geoprivacy=settings.PRIVACY_SETTING_PUBLIC).count()
        to_update = posts.exclude(geoprivacy=settings.PRIVACY_SETTING_PUBLIC)
        update_count = to_update.count()

        self.stdout.write(
            f"  already public : {already_public}\n"
            f"  to be updated  : {update_count}"
        )

        if update_count == 0:
            self.stdout.write(self.style.SUCCESS("All matched posts are already public. Done."))
            return

        if dry_run:
            for post in to_update.select_related():
                lat = post.true_location_spatial.y if post.true_location_spatial else None
                lon = post.true_location_spatial.x if post.true_location_spatial else None
                self.stdout.write(
                    f"  [dry-run] {post.id}  geoprivacy={post.geoprivacy!r} → 'public'"
                    f"  lat={lat}  lon={lon}"
                )
            self.stdout.write(self.style.WARNING("Dry run — no changes written."))
            return

        # Perform the update post-by-post so we can copy coordinates correctly.
        updated = 0
        no_coords = 0
        for post in to_update.iterator():
            if post.true_location_spatial:
                lat = post.true_location_spatial.y
                lon = post.true_location_spatial.x
            elif post.public_location_latitude is not None:
                # Already has public coords stored (e.g. was obscured but had public fallback)
                lat = post.public_location_latitude
                lon = post.public_location_longitude
            else:
                self.stderr.write(
                    self.style.WARNING(
                        f"  SKIP {post.id} — no coordinates stored; cannot set public location."
                    )
                )
                no_coords += 1
                continue

            post.geoprivacy = settings.PRIVACY_SETTING_PUBLIC
            post.public_location_latitude = lat
            post.public_location_longitude = lon
            post.save(update_fields=["geoprivacy", "public_location_latitude", "public_location_longitude"])
            self.stdout.write(f"  ✓ {post.id}  lat={lat:.5f}  lon={lon:.5f}")
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. updated={updated}  skipped_no_coords={no_coords}  already_public={already_public}"
            )
        )
