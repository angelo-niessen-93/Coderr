"""Views for offer API endpoints."""

from decimal import Decimal, InvalidOperation

from django.db.models import Min, Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from offers_app.api.pagination import OfferPagination
from offers_app.api.permissions import IsBusinessUser, IsOfferOwner
from offers_app.api.serializers import (
    OfferDetailSerializer,
    OfferListSerializer,
    OfferRetrieveSerializer,
    OfferWriteResponseSerializer,
    OfferWriteSerializer,
)
from offers_app.models import Offer, OfferDetail


class OfferListCreateView(ListCreateAPIView):
    """List public offers or create offers for business users."""

    http_method_names = ['get', 'post', 'head', 'options']
    pagination_class = OfferPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsBusinessUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OfferWriteSerializer
        return OfferListSerializer

    def get_queryset(self):
        queryset = self._base_queryset()
        queryset = self._filter_creator(queryset)
        queryset = self._filter_min_price(queryset)
        queryset = self._filter_max_delivery_time(queryset)
        queryset = self._filter_search(queryset)
        return self._order_queryset(queryset)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(user=request.user)
        response_serializer = self._response_serializer(offer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _base_queryset(self):
        return Offer.objects.select_related('user').prefetch_related(
            'details',
        ).annotate(
            calculated_min_price=Min('details__price'),
            calculated_min_delivery_time=Min('details__delivery_time_in_days'),
        )

    def _filter_creator(self, queryset):
        creator_id = self.request.query_params.get('creator_id')
        if creator_id is None:
            return queryset
        return queryset.filter(user_id=self._positive_int('creator_id'))

    def _filter_min_price(self, queryset):
        min_price = self.request.query_params.get('min_price')
        if min_price is None:
            return queryset
        return queryset.filter(calculated_min_price__gte=self._decimal())

    def _filter_max_delivery_time(self, queryset):
        max_time = self.request.query_params.get('max_delivery_time')
        if max_time is None:
            return queryset
        value = self._positive_int('max_delivery_time')
        return queryset.filter(calculated_min_delivery_time__lte=value)

    def _filter_search(self, queryset):
        search = self.request.query_params.get('search')
        if not search:
            return queryset
        return queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    def _order_queryset(self, queryset):
        ordering = self.request.query_params.get('ordering')
        allowed = {'updated_at', '-updated_at', 'min_price', '-min_price'}
        if ordering is None:
            return queryset.order_by('-updated_at', '-created_at', 'id')
        if ordering not in allowed:
            raise ValidationError({'ordering': 'Invalid ordering field.'})
        return queryset.order_by(self._ordering_field(ordering))

    def _ordering_field(self, ordering):
        if ordering == 'min_price':
            return 'calculated_min_price'
        if ordering == '-min_price':
            return '-calculated_min_price'
        return ordering

    def _positive_int(self, param):
        try:
            value = int(self.request.query_params[param])
        except ValueError as exc:
            raise ValidationError({param: 'Must be an integer.'}) from exc
        if value <= 0:
            raise ValidationError({param: 'Must be positive.'})
        return value

    def _decimal(self):
        try:
            value = Decimal(self.request.query_params['min_price'])
        except InvalidOperation as exc:
            raise ValidationError({'min_price': 'Must be numeric.'}) from exc
        if value < 0:
            raise ValidationError({'min_price': 'Must not be negative.'})
        return value

    def _response_serializer(self, offer):
        return OfferWriteResponseSerializer(
            offer,
            context=self.get_serializer_context(),
        )


class OfferRetrieveView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete one offer by offer ID."""

    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Offer.objects.select_related('user').prefetch_related(
            'details',
        ).annotate(
            calculated_min_price=Min('details__price'),
            calculated_min_delivery_time=Min('details__delivery_time_in_days'),
        )

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAuthenticated(), IsOfferOwner()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return OfferWriteSerializer
        return OfferRetrieveSerializer

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        response.data = self._response_serializer(self.object).data
        return response

    def perform_update(self, serializer):
        self.object = serializer.save()

    def _response_serializer(self, offer):
        return OfferWriteResponseSerializer(
            offer,
            context=self.get_serializer_context(),
        )


class OfferDetailRetrieveView(RetrieveAPIView):
    """Retrieve one offer detail by offer detail ID."""

    permission_classes = [IsAuthenticated]
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailSerializer
