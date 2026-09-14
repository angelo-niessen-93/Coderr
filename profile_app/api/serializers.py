"""Serializers for profile API endpoints."""

from rest_framework import serializers

from profile_app.models import Profile


class EmptyStringRepresentationMixin:
    """Return empty strings for nullable text values."""

    empty_string_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in self.empty_string_fields:
            if data.get(field) is None:
                data[field] = ''
        return data


class ProfileDetailSerializer(
    EmptyStringRepresentationMixin,
    serializers.ModelSerializer,
):
    """Detailed profile data including editable user fields."""

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(
        source='user.first_name',
        required=False,
        allow_blank=True,
    )
    last_name = serializers.CharField(
        source='user.last_name',
        required=False,
        allow_blank=True,
    )
    email = serializers.EmailField(source='user.email', required=False)

    empty_string_fields = (
        'first_name',
        'last_name',
        'location',
        'tel',
        'description',
        'working_hours',
    )

    class Meta:
        model = Profile
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at',
        ]
        read_only_fields = ['user', 'username', 'type', 'created_at']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        self._update_user(instance.user, user_data)
        return self._update_profile(instance, validated_data)

    def _update_user(self, user, user_data):
        for field, value in user_data.items():
            setattr(user, field, value)
        if user_data:
            user.save()

    def _update_profile(self, instance, profile_data):
        for field, value in profile_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class BusinessProfileListSerializer(
    EmptyStringRepresentationMixin,
    serializers.ModelSerializer,
):
    """Business profile list data."""

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    empty_string_fields = (
        'first_name',
        'last_name',
        'location',
        'tel',
        'description',
        'working_hours',
    )

    class Meta:
        model = Profile
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
        ]


class CustomerProfileListSerializer(
    EmptyStringRepresentationMixin,
    serializers.ModelSerializer,
):
    """Customer profile list data."""

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    uploaded_at = serializers.DateTimeField(source='created_at', read_only=True)

    empty_string_fields = ('first_name', 'last_name')

    class Meta:
        model = Profile
        fields = [
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'uploaded_at',
            'type',
        ]
