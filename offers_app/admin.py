from django.contrib import admin

from offers_app.models import Offer, OfferDetail


class OfferDetailInline(admin.TabularInline):
    """Inline editing for offer details."""

    model = OfferDetail
    extra = 0


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Admin configuration for offers."""

    inlines = [OfferDetailInline]
    list_display = ['title', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'description', 'user__username']


@admin.register(OfferDetail)
class OfferDetailAdmin(admin.ModelAdmin):
    """Admin configuration for offer details."""

    list_display = ['title', 'offer', 'offer_type', 'price']
    list_filter = ['offer_type']
    search_fields = ['title', 'offer__title']
