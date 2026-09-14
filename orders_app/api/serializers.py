"""Serializers for order API endpoints."""

from copy import deepcopy

from django.db import transaction
from rest_framework import serializers

from orders_app.models import Order


class OrderSerializer(serializers.ModelSerializer):
    """Read representation for orders."""

    class Meta:
        model = Order
        fields = [
            'id',
            'customer_user',
            'business_user',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """Validate order creation input and create an order snapshot."""

    offer_detail_id = serializers.IntegerField()

    def validate(self, attrs):
        unexpected_fields = set(self.initial_data) - {'offer_detail_id'}
        if unexpected_fields:
            raise serializers.ValidationError(
                'Only offer_detail_id can be supplied.'
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        customer_user = validated_data['customer_user']
        offer_detail = validated_data['offer_detail']
        return Order.objects.create(
            customer_user=customer_user,
            business_user=offer_detail.offer.user,
            title=offer_detail.title,
            revisions=offer_detail.revisions,
            delivery_time_in_days=offer_detail.delivery_time_in_days,
            price=offer_detail.price,
            features=deepcopy(offer_detail.features),
            offer_type=offer_detail.offer_type,
        )


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Allow status-only order updates."""

    class Meta:
        model = Order
        fields = ['status']

    def validate(self, attrs):
        if 'status' not in self.initial_data:
            raise serializers.ValidationError(
                {'status': 'This field is required.'}
            )
        unexpected_fields = set(self.initial_data) - {'status'}
        if unexpected_fields:
            raise serializers.ValidationError('Only status can be updated.')
        return attrs
