from django.conf import settings
from django.shortcuts import render
from rest_framework import authentication, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from siteapps.socialmedia.models import MediaPost


# Create your views here.
class UserProfileView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "joined_date": request.user.created.strftime(settings.READABLE_DATE_FORMAT),
            "display_name": request.user.name,
            "sightings_count": MediaPost.objects.filter(created_by=request.user).count(),
        }

        return Response(status=status.HTTP_200_OK, data=data)
