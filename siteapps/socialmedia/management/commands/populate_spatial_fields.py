"""
Management command to populate spatial point fields from existing latitude/longitude data.

This command iterates through all MediaPost objects and populates the three spatial fields:
- public_location_spatial
- true_location_spatial
- private_location_spatial

It uses the existing latitude and longitude float fields to create Point geometries.
"""

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from siteapps.socialmedia.models import MediaPost


class Command(BaseCommand):
    help = 'Populate spatial point fields from existing latitude/longitude data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to process in each batch (default: 500)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving changes',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))

        # Count total posts
        total_posts = MediaPost.objects.count()
        self.stdout.write(f'Found {total_posts} total MediaPost objects')

        # Count posts that need updates
        posts_needing_update = MediaPost.objects.filter(
            # Posts with public location but no spatial field
            public_location_latitude__isnull=False,
            public_location_longitude__isnull=False,
            public_location_spatial__isnull=True
        ) | MediaPost.objects.filter(
            # Posts with true location but no spatial field
            true_location_latitude__isnull=False,
            true_location_longitude__isnull=False,
            true_location_spatial__isnull=True
        ) | MediaPost.objects.filter(
            # Posts with private location but no spatial field
            private_location_latitude__isnull=False,
            private_location_longitude__isnull=False,
            private_location_spatial__isnull=True
        )

        count_needing_update = posts_needing_update.count()
        self.stdout.write(f'Found {count_needing_update} MediaPost objects needing spatial data updates')

        if count_needing_update == 0:
            self.stdout.write(self.style.SUCCESS('All spatial fields are already populated!'))
            return

        # Process in batches
        updated_count = 0
        public_updated = 0
        true_updated = 0
        private_updated = 0

        # Get all posts that need updating (distinct)
        posts_to_update = MediaPost.objects.filter(
            pk__in=posts_needing_update.values_list('pk', flat=True)
        ).distinct()

        for i in range(0, posts_to_update.count(), batch_size):
            batch = posts_to_update[i:i + batch_size]

            with transaction.atomic():
                for post in batch:
                    modified = False

                    # Update public location spatial if needed
                    if (post.public_location_latitude is not None and 
                        post.public_location_longitude is not None and 
                        post.public_location_spatial is None):
                        post.public_location_spatial = Point(
                            post.public_location_longitude,
                            post.public_location_latitude,
                            srid=4326
                        )
                        public_updated += 1
                        modified = True

                    # Update true location spatial if needed
                    if (post.true_location_latitude is not None and 
                        post.true_location_longitude is not None and 
                        post.true_location_spatial is None):
                        post.true_location_spatial = Point(
                            post.true_location_longitude,
                            post.true_location_latitude,
                            srid=4326
                        )
                        true_updated += 1
                        modified = True

                    # Update private location spatial if needed
                    if (post.private_location_latitude is not None and 
                        post.private_location_longitude is not None and 
                        post.private_location_spatial is None):
                        post.private_location_spatial = Point(
                            post.private_location_longitude,
                            post.private_location_latitude,
                            srid=4326
                        )
                        private_updated += 1
                        modified = True

                    if modified:
                        if not dry_run:
                            post.save(update_fields=[
                                'public_location_spatial',
                                'true_location_spatial',
                                'private_location_spatial'
                            ])
                        updated_count += 1

            self.stdout.write(f'Processed {min(i + batch_size, posts_to_update.count())}/{posts_to_update.count()} posts')

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nSummary:'))
        self.stdout.write(f'  Total posts updated: {updated_count}')
        self.stdout.write(f'  Public location spatial fields populated: {public_updated}')
        self.stdout.write(f'  True location spatial fields populated: {true_updated}')
        self.stdout.write(f'  Private location spatial fields populated: {private_updated}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN complete - no changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nSpatial data population complete!'))
