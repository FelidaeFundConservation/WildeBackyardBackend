# Manual migration to remove public_location_spatial and private_location_spatial fields
# Keep only true_location_spatial as the canonical source

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('socialmedia', '0013_mediapost_private_location_spatial_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mediapost',
            name='public_location_spatial',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='private_location_spatial',
        ),
    ]
