"""Serializers for offer API endpoints."""

from django.db import transaction
from rest_framework import serializers

from offers_app.models import Offer, OfferDetail


class OfferDetailSerializer(serializers.ModelSerializer):
    """Full offer detail representation."""

    class Meta:
        model = OfferDetail
        fields = [
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        ]

    def validate_delivery_time_in_days(self, value):
        """Require a positive delivery time."""
        if value <= 0:
            raise serializers.ValidationError('Must be positive.')
        return value

    def validate_price(self, value):
        """Reject negative offer detail prices."""
        if value < 0:
            raise serializers.ValidationError('Must not be negative.')
        return value

    def validate_features(self, value):
        """Ensure features are represented as a list of strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Must be a list.')
        if not all(isinstance(feature, str) for feature in value):
            raise serializers.ValidationError('Each feature must be a string.')
        return value


class OfferDetailLinkSerializer(serializers.ModelSerializer):
    """Compact link representation for an offer detail."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']

    def get_url(self, obj):
        """Build the API URL for an offer detail."""
        path = f'/api/offerdetails/{obj.id}/'
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(path)
        return path


class UserDetailsSerializer(serializers.Serializer):
    """Small related user representation for offer lists."""

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()


class OfferMetricsMixin:
    """Calculated offer values shared by read serializers."""

    def get_min_price(self, obj):
        """Return the lowest related detail price."""
        if hasattr(obj, 'calculated_min_price'):
            return obj.calculated_min_price
        prices = obj.details.values_list('price', flat=True)
        return min(prices, default=None)

    def get_min_delivery_time(self, obj):
        """Return the shortest related delivery time."""
        if hasattr(obj, 'calculated_min_delivery_time'):
            return obj.calculated_min_delivery_time
        times = obj.details.values_list('delivery_time_in_days', flat=True)
        return min(times, default=None)


class OfferListSerializer(OfferMetricsMixin, serializers.ModelSerializer):
    """Offer list representation."""

    details = OfferDetailLinkSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()
    user_details = UserDetailsSerializer(source='user', read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id',
            'user',
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details',
            'min_price',
            'min_delivery_time',
            'user_details',
        ]


class OfferRetrieveSerializer(OfferMetricsMixin, serializers.ModelSerializer):
    """Offer detail read representation."""

    details = OfferDetailLinkSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            'id',
            'user',
            'title',
            'image',
            'description',
            'created_at',
            'updated_at',
            'details',
            'min_price',
            'min_delivery_time',
        ]


class OfferWriteSerializer(serializers.ModelSerializer):
    """Create and update offers with nested details."""

    details = OfferDetailSerializer(many=True, required=False)
    image = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Offer
        fields = ['title', 'image', 'description', 'details']

    def __init__(self, *args, **kwargs):
        """Propagate partial updates into nested detail serializers."""
        super().__init__(*args, **kwargs)
        if self.partial:
            self.fields['details'].child.partial = True

    def validate(self, attrs):
        """Validate nested detail requirements for create and update."""
        details = attrs.get('details')
        if self.instance is None:
            self._validate_create_details(details)
        if self.instance is not None and details is not None:
            self._validate_update_details(details)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create an offer with its required nested details atomically."""
        details_data = validated_data.pop('details')
        offer = Offer.objects.create(**validated_data)
        self._create_details(offer, details_data)
        return offer

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update an offer and any supplied nested details atomically."""
        details_data = validated_data.pop('details', [])
        self._update_offer(instance, validated_data)
        self._update_details(instance, details_data)
        return instance

    def _validate_create_details(self, details):
        """Require exactly three details for new offers."""
        if len(details or []) != 3:
            raise serializers.ValidationError(
                {'details': 'Exactly three details are required.'}
            )
        self._validate_offer_types(details)

    def _validate_offer_types(self, details):
        """Require basic, standard, and premium detail types."""
        expected = self._expected_offer_types()
        actual = {detail['offer_type'] for detail in details}
        if actual != expected:
            raise serializers.ValidationError(
                {'details': 'Details must be basic, standard, and premium.'}
            )

    def _expected_offer_types(self):
        """Return the required set of offer detail types."""
        return {
            OfferDetail.BASIC,
            OfferDetail.STANDARD,
            OfferDetail.PREMIUM,
        }

    def _validate_update_details(self, details):
        """Validate supplied detail types against existing details."""
        existing_types = set(
            self.instance.details.values_list('offer_type', flat=True)
        )
        for detail in details:
            self._validate_update_detail_type(detail, existing_types)

    def _validate_update_detail_type(self, detail, existing_types):
        """Reject missing or unknown detail types during updates."""
        offer_type = detail.get('offer_type')
        if offer_type is None:
            raise serializers.ValidationError(
                {'details': 'offer_type is required for detail updates.'}
            )
        if offer_type not in existing_types:
            raise serializers.ValidationError(
                {'details': 'Unknown offer detail type.'}
            )

    def _create_details(self, offer, details_data):
        """Create all nested detail rows for an offer."""
        for detail_data in details_data:
            OfferDetail.objects.create(offer=offer, **detail_data)

    def _update_offer(self, instance, offer_data):
        """Persist direct Offer field changes."""
        for field, value in offer_data.items():
            setattr(instance, field, value)
        instance.save()

    def _update_details(self, instance, details_data):
        """Apply nested updates to existing details by offer type."""
        details_by_type = {
            detail.offer_type: detail for detail in instance.details.all()
        }
        for detail_data in details_data:
            self._update_detail(details_by_type, detail_data)

    def _update_detail(self, details_by_type, detail_data):
        """Select the existing detail and save supplied changes."""
        offer_type = detail_data['offer_type']
        detail = details_by_type.get(offer_type)
        if detail is None:
            raise serializers.ValidationError('Unknown offer detail type.')
        self._save_detail(detail, detail_data)

    def _save_detail(self, detail, detail_data):
        """Persist changed fields on an offer detail."""
        for field, value in detail_data.items():
            setattr(detail, field, value)
        detail.save()


class OfferWriteResponseSerializer(serializers.ModelSerializer):
    """Offer response after create or update."""

    details = OfferDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Offer
        fields = ['id', 'title', 'image', 'description', 'details']
