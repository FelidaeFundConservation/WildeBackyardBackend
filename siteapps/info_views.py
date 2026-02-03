"""
Views for application information endpoints.
"""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.version import VERSION


@extend_schema(
    summary="Get application version information",
    description="Returns the current commit hash and release tag of the deployed application",
    responses={
        200: inline_serializer(
            name="VersionInfoResponse",
            fields={
                "commit_hash": serializers.CharField(),
                "release_tag": serializers.CharField(),
            },
        )
    },
    tags=["Info"],
)
class VersionInfoView(APIView):
    """API endpoint that returns version information."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Return the commit hash and release tag."""
        return Response(
            status=status.HTTP_200_OK,
            data={
                "commit_hash": VERSION["commit_hash"],
                "release_tag": VERSION["release_tag"],
            },
        )
