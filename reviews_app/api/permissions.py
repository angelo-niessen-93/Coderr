"""Custom permissions for review API endpoints."""

from rest_framework.permissions import BasePermission

from profile_app.models import Profile


class IsCustomerReviewer(BasePermission):
    """Allow review creation only for authenticated customers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        return profile is not None and profile.type == Profile.CUSTOMER


class IsReviewOwner(BasePermission):
    """Allow review edits only by the original reviewer."""

    def has_object_permission(self, request, view, obj):
        return obj.reviewer == request.user


