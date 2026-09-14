from django.contrib import admin

from reviews_app.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'business_user', 'reviewer', 'rating', 'created_at']
    list_filter = ['rating', 'created_at', 'updated_at']
    search_fields = ['business_user__username', 'reviewer__username']
