"""Views for order API endpoints."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from offers_app.models import OfferDetail
from orders_app.api.permissions import (
    IsCustomerUser,
    IsOrderBusinessUser,
    IsStaffUser,
)
from orders_app.api.serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
)
from orders_app.models import Order
from profile_app.models import Profile


class OrderListCreateView(ListCreateAPIView):
    """List involved orders or create an order snapshot."""

    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsCustomerUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(
            Q(customer_user=self.request.user) |
            Q(business_user=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer_detail = self._get_offer_detail(serializer)
        order = serializer.save(
            customer_user=request.user,
            offer_detail=offer_detail,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def _get_offer_detail(self, serializer):
        offer_detail_id = serializer.validated_data['offer_detail_id']
        return get_object_or_404(OfferDetail, pk=offer_detail_id)


class OrderStatusUpdateView(RetrieveUpdateDestroyAPIView):
    """Update an order status or delete an order by order ID."""

    http_method_names = ['patch', 'delete', 'head', 'options']
    queryset = Order.objects.all()
    serializer_class = OrderStatusUpdateSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsStaffUser()]
        return [IsAuthenticated(), IsOrderBusinessUser()]

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        response.data = OrderSerializer(self.object).data
        return response

    def perform_update(self, serializer):
        self.object = serializer.save()


class OrderCountView(APIView):
    """Return in-progress order count for a business user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        self._get_business_profile(business_user_id)
        return Response({
            'order_count': self._in_progress_count(business_user_id),
        })

    def _get_business_profile(self, business_user_id):
        return get_object_or_404(
            Profile,
            user_id=business_user_id,
            type=Profile.BUSINESS,
        )

    def _in_progress_count(self, business_user_id):
        return Order.objects.filter(
            business_user_id=business_user_id,
            status=Order.IN_PROGRESS,
        ).count()
