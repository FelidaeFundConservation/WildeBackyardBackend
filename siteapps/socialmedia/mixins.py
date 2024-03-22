from django.conf import settings
from rest_framework import status
from rest_framework.response import Response


class LatLngValidationMixin:
    def validate_latitude_longitude(self, latitude, longitude):
        # Check the values exist
        if not latitude and not longitude:
            return createResponse400("Latitude and longitude values were both not provided.")
        elif not latitude:
            return createResponse400("Latitude value was not provided.")
        elif not longitude:
            return createResponse400("Longitude value was not provided.")

        # If they exist, check the values are valid
        latitude_valid = -90 < float(latitude) < 90
        longitude_valid = -180 < float(longitude) < 180

        if not latitude_valid and not longitude_valid:
            return createResponse400(
                "Both latitude and longitude values are invalid (must provide a value between -90 and 90 for latitude; -180 and 180 for longitude)."
            )
        elif not latitude_valid:
            return createResponse400("Latitude value is invalid (must provide a value between -90 and 90).")
        elif not longitude_valid:
            return createResponse400("Longitude value is invalid (must provide a value between -180 and 180).")
        else:
            return None


class PrivacySettingValidationMixin:
    def validate_privacy_setting(self, privacy_setting):
        if privacy_setting is None:
            return createResponse400(
                "No privacy setting provided. Please provide a setting ('public', 'obfuscated', or 'private')."
            )
        elif (
            privacy_setting != settings.PRIVACY_SETTING_PUBLIC
            and privacy_setting != settings.PRIVACY_SETTING_OBFUSCATED
            and privacy_setting != settings.PRIVACY_SETTING_PRIVATE
        ):
            return createResponse400(
                f"Invalid privacy setting '{privacy_setting}' provided. Must be 'public', 'obfuscated', or 'private'."
            )
        else:
            return None


# Check whether required combinations of arguments exists
class PostInputsValidationMixin:
    def validate_arguments_exist(
        self,
        privacy_setting,
        encounter_datetime,
        accuracy_meters,
        obfuscation_kilometers,
        obfuscation_box_corners,
        geocoded_location_name,
        research_use_allowed,
    ):
        # The geocoded location from the coordinates
        if geocoded_location_name is None or len(geocoded_location_name) == 0:
            return createResponse400("Empty or no geocoded location name provided.")

        # Datetime string to convert
        if encounter_datetime is None:
            return createResponse400("No encounter datetime provided.")

        # Whether public research is allowed to use the post's info
        if research_use_allowed is None:
            return createResponse400("No 'research use allowed' preference provided.")

        # A ring where the true location may lie
        if accuracy_meters is None:
            return createResponse400(
                "No location accuracy provided. Must be a meter value above 0, or exactly 0 for 'No Accuracy Info.'"
            )

        # Privacy-setting specific checks
        if privacy_setting == settings.PRIVACY_SETTING_OBFUSCATED:
            if obfuscation_kilometers < 1 or obfuscation_kilometers > 10:
                return createResponse400("Invalid obfuscation range. Must be between 1 and 10 kilometers.")


def createResponse400(message):
    return Response(
        status=status.HTTP_400_BAD_REQUEST,
        data={"error": message},
    )
