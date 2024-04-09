from django.shortcuts import render
from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.species.models import SpeciesName


# Create your views here.
class GetSpeciesNamesView(APIView):
    def get(self, request):
        species_names = list(SpeciesName.objects.all().values_list("name", flat=True))
        return Response(status=status.HTTP_200_OK, data=species_names)
