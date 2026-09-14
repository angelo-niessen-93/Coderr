"""Views for review API endpoints."""

from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from reviews_app.api.permissions import IsCustomerReviewer
from reviews_app.api.serializers import ReviewSerializer
from reviews_app.models import Review


class ReviewListCreateView(ListCreateAPIView):
    """List reviews or create a customer review."""

    serializer_class = ReviewSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCustomerReviewer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Review.objects.select_related('business_user', 'reviewer')
        queryset = self._filter_queryset(queryset)
        ordering = self.request.query_params.get('ordering')
        if ordering in self._allowed_ordering():
            return queryset.order_by(ordering)
        return queryset

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)

    def _filter_queryset(self, queryset):
        filters = {}
        self._add_filter(filters, 'business_user_id')
        self._add_filter(filters, 'reviewer_id')
        return queryset.filter(**filters)

    def _add_filter(self, filters, field):
        value = self.request.query_params.get(field)
        if value is not None:
            filters[field] = value

    def _allowed_ordering(self):
        return {'updated_at', '-updated_at', 'rating', '-rating'}
