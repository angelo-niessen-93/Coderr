from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class OfferPagination(PageNumberPagination):
    """Page-number pagination with validated client page size."""

    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 20

    def get_page_size(self, request):
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size is None:
            return self.page_size
        return self._validated_page_size(page_size)

    def _validated_page_size(self, value):
        try:
            page_size = int(value)
        except ValueError as exc:
            raise ValidationError({'page_size': 'Must be an integer.'}) from exc
        if page_size <= 0:
            raise ValidationError({'page_size': 'Must be positive.'})
        return min(page_size, self.max_page_size)
