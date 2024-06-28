import json

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


class ChangeUsernameView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        new_username = data.get("newUsername")

        if len(new_username) < 3:
            message = "Username must be at least 3 characters long."

            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": message},
            )

        request.user.name = new_username
        request.user.save()

        return Response(status=status.HTTP_200_OK)


class DeleteAccountView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)

        confirmation_string = data.get("confirmation_string")

        # Confirm user input to delete account
        if confirmation_string == self.request.user.name:
            self.request.user.delete()
            return Response(status=status.HTTP_200_OK)
        else:
            message = "The account deletion code was not input correctly."
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"error": message},
            )
