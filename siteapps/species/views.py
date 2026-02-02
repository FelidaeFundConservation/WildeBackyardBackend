import json

from django.shortcuts import render
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import authentication, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.species.models import SpeciesName


# Create your views here.
@extend_schema(
    summary="Get all species names",
    description="Retrieve a list of all available species names",
    responses={
        200: inline_serializer(
            name="SpeciesNamesResponse", fields={"species_names": serializers.ListField(child=serializers.CharField())}
        )
    },
    tags=["Species"],
)
class GetSpeciesNamesView(APIView):
    def get(self, request):
        species_names = list(SpeciesName.objects.all().values_list("name", flat=True))
        data = {"species_names": species_names}
        return Response(status=status.HTTP_200_OK, data=data)


@extend_schema(
    summary="Create a new species name",
    description="Add a new species name to the database",
    request=inline_serializer(name="CreateSpeciesRequest", fields={"name": serializers.CharField()}),
    responses={201: None, 400: inline_serializer(name="ErrorResponse", fields={"error": serializers.CharField()})},
    tags=["Species"],
)
class CreateSpeciesNameView(APIView):
    def post(self, request):
        data = json.loads(request.body)

        species_name = data.get("name")

        if species_name is None:
            message = "Species name was not provided."

            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": message},
            )
        else:
            # Names should be in title case to avoid duplications
            species_name = species_name.title()
            # Create a new species with name if it doesn't exist
            SpeciesName.objects.get_or_create(name=species_name)

        return Response(status=status.HTTP_201_CREATED)
