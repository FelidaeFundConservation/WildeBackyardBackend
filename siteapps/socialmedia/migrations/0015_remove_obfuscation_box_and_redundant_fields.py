# Remove obfuscation_box corner fields and redundant lat/lng fields
# Keep only true_location_spatial as the canonical location source

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('socialmedia', '0014_remove_public_private_spatial_fields'),
    ]

    operations = [
        # Remove obfuscation box corner fields
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_1_latitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_1_longitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_2_latitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_2_longitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_3_latitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_3_longitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_4_latitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='obfuscation_box_corner_4_longitude',
        ),
        # Remove redundant lat/lng fields (we now use only true_location_spatial)
        migrations.RemoveField(
            model_name='mediapost',
            name='true_location_latitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='true_location_longitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='private_location_latitude',
        ),
        migrations.RemoveField(
            model_name='mediapost',
            name='private_location_longitude',
        ),
    ]
