"""Serializers for authentication API endpoints."""

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from profile_app.models import Profile


User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    """Validate registration data and create the user profile pair."""

    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    repeated_password = serializers.CharField(write_only=True)
    type = serializers.ChoiceField(choices=Profile.PROFILE_TYPE_CHOICES)

    def validate_username(self, value):
        """Reject usernames that are already registered."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        """Reject email addresses that are already registered."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('This email is already taken.')
        return value

    def validate(self, attrs):
        """Ensure both submitted passwords match."""
        if attrs['password'] != attrs['repeated_password']:
            raise serializers.ValidationError(
                {'repeated_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        """Create a user, profile, and authentication token."""
        profile_type = validated_data.pop('type')
        validated_data.pop('repeated_password')
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, type=profile_type)
        token, _ = Token.objects.get_or_create(user=user)
        return {'user': user, 'token': token.key}


class LoginSerializer(serializers.Serializer):
    """Validate login credentials with Django authentication."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticate credentials with Django and attach the user."""
        user = authenticate(
            username=attrs['username'],
            password=attrs['password'],
        )
        if user is None:
            raise serializers.ValidationError('Invalid credentials.')
        attrs['user'] = user
        return attrs
