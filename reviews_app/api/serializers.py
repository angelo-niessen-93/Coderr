"""Serializers for review API endpoints."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from profile_app.models import Profile
from reviews_app.models import Review


User = get_user_model()


class ReviewSerializer(serializers.ModelSerializer):
    """Review response and creation validation."""

    business_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
    )

    class Meta:
        model = Review
        fields = [
            'id',
            'business_user',
            'reviewer',
            'rating',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at']

    def validate(self, attrs):
        self._validate_create_fields()
        self._validate_unique_review(attrs)
        return attrs

    def validate_business_user(self, value):
        profile = getattr(value, 'profile', None)
        if profile is None or profile.type != Profile.BUSINESS:
            raise serializers.ValidationError('Must be a business user.')
        return value

    def _validate_create_fields(self):
        writable_fields = {'business_user', 'rating', 'description'}
        unexpected_fields = set(self.initial_data) - writable_fields
        if unexpected_fields:
            raise serializers.ValidationError(
                'Only business_user, rating, and description can be supplied.'
            )

    def _validate_unique_review(self, attrs):
        reviewer = self._get_reviewer()
        business_user = attrs.get('business_user')
        if not reviewer or not business_user:
            return
        if self._review_exists(reviewer, business_user):
            raise serializers.ValidationError('Review already exists.')

    def _get_reviewer(self):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return request.user
        return self.context.get('reviewer')

    def _review_exists(self, reviewer, business_user):
        return Review.objects.filter(
            reviewer=reviewer,
            business_user=business_user,
        ).exists()


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Allow rating and description updates only."""

    class Meta:
        model = Review
        fields = ['rating', 'description']

    def validate(self, attrs):
        allowed_fields = {'rating', 'description'}
        unexpected_fields = set(self.initial_data) - allowed_fields
        if unexpected_fields:
            raise serializers.ValidationError(
                'Only rating and description can be updated.'
            )
        return attrs

