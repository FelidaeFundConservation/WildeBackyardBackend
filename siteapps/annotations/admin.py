from django.contrib import admin

from .models import MegaDetectorAnnotation, MegaDetectorBoundingBox, SpeciesNetAnnotation, SpeciesNetPrediction


@admin.register(MegaDetectorAnnotation)
class MegaDetectorAnnotationAdmin(admin.ModelAdmin):
    list_display = ("id", "media", "model_version", "max_detection_conf", "created")
    list_filter = ("model_version",)
    search_fields = ("media__id",)


@admin.register(MegaDetectorBoundingBox)
class MegaDetectorBoundingBoxAdmin(admin.ModelAdmin):
    list_display = ("id", "annotation", "category", "confidence")
    list_filter = ("category",)


@admin.register(SpeciesNetAnnotation)
class SpeciesNetAnnotationAdmin(admin.ModelAdmin):
    list_display = ("id", "media", "model_version", "megadetector_bbox", "created")
    list_filter = ("model_version",)
    search_fields = ("media__id",)


@admin.register(SpeciesNetPrediction)
class SpeciesNetPredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "annotation", "rank", "scientific_name", "common_name", "confidence")
    list_filter = ("rank",)
    search_fields = ("scientific_name", "common_name")
