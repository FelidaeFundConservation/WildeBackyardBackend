"""
Custom serializers for dj-rest-auth registration.
"""
from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from rest_framework import serializers


class RegisterSerializer(BaseRegisterSerializer):
    """
    Custom registration serializer that removes username field
    and adds name field for our User model.
    """
    name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Display name (optional, will be auto-generated if not provided)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field completely
        if 'username' in self.fields:
            del self.fields['username']
    
    def get_cleaned_data(self):
        """Include name in cleaned data."""
        data = super().get_cleaned_data()
        data['name'] = self.validated_data.get('name', '')
        return data
