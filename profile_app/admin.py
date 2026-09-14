from django.contrib import admin

from profile_app.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin configuration for Coderr user profiles."""

    list_display = ['user', 'type', 'location', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['user__username', 'user__email', 'location', 'tel']
    readonly_fields = ['created_at']
