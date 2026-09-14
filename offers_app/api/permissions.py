"""Custom permissions for offer API endpoints."""

from rest_framework.permissions import BasePermission

from profile_app.models import Profile


class IsBusinessUser(BasePermission):
    """Allow access only to authenticated business users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        return profile is not None and profile.type == Profile.BUSINESS


class IsOfferOwner(BasePermission):
    """Allow offer changes only for the creator."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
