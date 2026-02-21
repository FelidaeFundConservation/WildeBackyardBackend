import uuid

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("socialmedia", "0015_remove_obfuscation_box_and_redundant_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="MegaDetectorAnnotation",
            fields=[
                ("created", model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name="created")),
                ("modified", model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name="modified")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("model_version", models.CharField(max_length=64)),
                ("max_detection_conf", models.FloatField(blank=True, null=True)),
                ("raw_result", models.JSONField(blank=True, null=True)),
                (
                    "media",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="megadetector_annotations",
                        to="socialmedia.media",
                    ),
                ),
            ],
            options={
                "ordering": ["-created"],
            },
        ),
        migrations.CreateModel(
            name="MegaDetectorBoundingBox",
            fields=[
                ("created", model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name="created")),
                ("modified", model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name="modified")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "category",
                    models.CharField(
                        choices=[("animal", "Animal"), ("person", "Person"), ("vehicle", "Vehicle")],
                        max_length=16,
                    ),
                ),
                ("confidence", models.FloatField()),
                ("bbox_x", models.FloatField()),
                ("bbox_y", models.FloatField()),
                ("bbox_width", models.FloatField()),
                ("bbox_height", models.FloatField()),
                (
                    "annotation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bounding_boxes",
                        to="annotations.megadetectorannotation",
                    ),
                ),
            ],
            options={
                "ordering": ["-confidence"],
            },
        ),
        migrations.CreateModel(
            name="SpeciesNetAnnotation",
            fields=[
                ("created", model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name="created")),
                ("modified", model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name="modified")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("model_version", models.CharField(max_length=64)),
                ("raw_result", models.JSONField(blank=True, null=True)),
                (
                    "media",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="speciesnet_annotations",
                        to="socialmedia.media",
                    ),
                ),
                (
                    "megadetector_bbox",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="speciesnet_annotations",
                        to="annotations.megadetectorboundingbox",
                    ),
                ),
            ],
            options={
                "ordering": ["-created"],
            },
        ),
        migrations.CreateModel(
            name="SpeciesNetPrediction",
            fields=[
                ("created", model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name="created")),
                ("modified", model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name="modified")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("scientific_name", models.CharField(max_length=200)),
                ("common_name", models.CharField(blank=True, default="", max_length=200)),
                ("confidence", models.FloatField()),
                ("rank", models.PositiveIntegerField()),
                (
                    "annotation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="predictions",
                        to="annotations.speciesnetannotation",
                    ),
                ),
            ],
            options={
                "ordering": ["rank"],
                "unique_together": {("annotation", "rank")},
            },
        ),
    ]
