"""Custom permissions for profile API endpoints."""

from rest_framework.permissions import BasePermission


class IsProfileOwner(BasePermission):
    """Allow profile changes only for the related user."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
