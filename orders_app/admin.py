from django.contrib import admin

from orders_app.models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for orders."""

    list_display = [
        'title',
        'customer_user',
        'business_user',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'offer_type', 'created_at']
    search_fields = [
        'title',
        'customer_user__username',
        'business_user__username',
    ]
