from django.core.exceptions import ValidationError
from profanity_check import predict


def validate_no_profanity(value):
    """Raise ValidationError if the given text is detected as profane."""
    if value and predict([value])[0] == 1:
        raise ValidationError("This field contains inappropriate language.")
