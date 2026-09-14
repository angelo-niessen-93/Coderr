"""Views for profile API endpoints."""

from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from profile_app.api.permissions import IsProfileOwner
from profile_app.api.serializers import (
    BusinessProfileListSerializer,
    CustomerProfileListSerializer,
    ProfileDetailSerializer,
)
from profile_app.models import Profile


class ProfileDetailView(RetrieveUpdateAPIView):
    """Retrieve or update a profile by related user ID."""

    http_method_names = ['get', 'patch', 'head', 'options']
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileDetailSerializer

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == 'PATCH':
            permission_classes = [IsAuthenticated, IsProfileOwner]
        return [permission() for permission in permission_classes]

    def get_object(self):
        profile = get_object_or_404(Profile, user_id=self.kwargs['pk'])
        self.check_object_permissions(self.request, profile)
        return profile


class BusinessProfileListView(ListAPIView):
    """List business profiles."""

    permission_classes = [IsAuthenticated]
    serializer_class = BusinessProfileListSerializer

    def get_queryset(self):
        return Profile.objects.filter(
            type=Profile.BUSINESS,
        ).select_related('user')


class CustomerProfileListView(ListAPIView):
    """List customer profiles."""

    permission_classes = [IsAuthenticated]
    serializer_class = CustomerProfileListSerializer

    def get_queryset(self):
        return Profile.objects.filter(
            type=Profile.CUSTOMER,
        ).select_related('user')
