from django.urls import path

from siteapps.annotations.views import (
    CreateMegaDetectorAnnotationView,
    CreateSpeciesNetAnnotationView,
    GetMegaDetectorAnnotationsView,
    GetPostAnnotationsView,
    GetSpeciesNetAnnotationsView,
)

urlpatterns = [
    # MegaDetector
    path(
        "api/megadetector/create/",
        CreateMegaDetectorAnnotationView.as_view(),
        name="megadetector_create",
    ),
    path(
        "api/megadetector/<uuid:media_id>/",
        GetMegaDetectorAnnotationsView.as_view(),
        name="megadetector_get",
    ),
    # SpeciesNet
    path(
        "api/speciesnet/create/",
        CreateSpeciesNetAnnotationView.as_view(),
        name="speciesnet_create",
    ),
    path(
        "api/speciesnet/<uuid:media_id>/",
        GetSpeciesNetAnnotationsView.as_view(),
        name="speciesnet_get",
    ),
    # Combined post annotations
    path(
        "api/post/<uuid:post_id>/",
        GetPostAnnotationsView.as_view(),
        name="post_annotations_get",
    ),
]
