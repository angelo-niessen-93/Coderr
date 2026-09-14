"""Custom permissions for order API endpoints."""

from rest_framework.permissions import BasePermission

from profile_app.models import Profile


class IsCustomerUser(BasePermission):
    """Allow access only to authenticated customer users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        return profile is not None and profile.type == Profile.CUSTOMER


class IsOrderBusinessUser(BasePermission):
    """Allow order changes only for the assigned business user."""

    def has_object_permission(self, request, view, obj):
        profile = getattr(request.user, 'profile', None)
        return (
            obj.business_user == request.user and
            profile is not None and
            profile.type == Profile.BUSINESS
        )


class IsStaffUser(BasePermission):
    """Allow access only to authenticated staff users."""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )
