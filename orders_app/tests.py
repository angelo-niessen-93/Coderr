from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from offers_app.models import Offer, OfferDetail
from orders_app.api.serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
)
from orders_app.models import Order
from profile_app.models import Profile


User = get_user_model()


class OrderModelTests(TestCase):
    """Tests for order data model."""

    def setUp(self):
        self.customer = User.objects.create_user(username='customer')
        self.business = User.objects.create_user(username='business')
        self.order = self._create_order()

    def test_order_can_be_created(self):
        self.assertEqual(Order.objects.count(), 1)

    def test_customer_user_relation_works(self):
        self.assertEqual(self.order.customer_user, self.customer)

    def test_business_user_relation_works(self):
        self.assertEqual(self.order.business_user, self.business)

    def test_title_is_stored(self):
        self.assertEqual(self.order.title, 'Logo Design')

    def test_revisions_are_stored(self):
        self.assertEqual(self.order.revisions, 2)

    def test_delivery_time_in_days_is_stored(self):
        self.assertEqual(self.order.delivery_time_in_days, 5)

    def test_price_is_stored_correctly(self):
        self.assertEqual(self.order.price, Decimal('99.99'))

    def test_features_store_list_of_strings(self):
        self.order.refresh_from_db()
        self.assertEqual(self.order.features, ['Logo', 'Source file'])

    def test_offer_type_supports_basic_standard_premium(self):
        choices = dict(Order.OFFER_TYPE_CHOICES)
        self.assertIn(Order.BASIC, choices)
        self.assertIn(Order.STANDARD, choices)
        self.assertIn(Order.PREMIUM, choices)

    def test_default_status_is_in_progress(self):
        self.assertEqual(self.order.status, Order.IN_PROGRESS)

    def test_completed_status_is_supported(self):
        self.order.status = Order.COMPLETED
        self.order.save()
        self.assertEqual(self.order.status, Order.COMPLETED)

    def test_cancelled_status_is_supported(self):
        self.order.status = Order.CANCELLED
        self.order.save()
        self.assertEqual(self.order.status, Order.CANCELLED)

    def test_created_at_is_populated(self):
        self.assertIsNotNone(self.order.created_at)

    def test_updated_at_is_populated(self):
        self.assertIsNotNone(self.order.updated_at)

    def test_str_returns_readable_value(self):
        self.assertEqual(str(self.order), f'Order #{self.order.pk} - Logo Design')

    def test_reverse_relations_are_distinct(self):
        self.assertEqual(list(self.customer.customer_orders.all()), [self.order])
        self.assertEqual(list(self.business.business_orders.all()), [self.order])

    def _create_order(self):
        return Order.objects.create(
            customer_user=self.customer,
            business_user=self.business,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
        )


class OrderSerializerTests(TestCase):
    """Tests for order API serializers."""

    def setUp(self):
        self.customer = User.objects.create_user(username='customer')
        self.business = User.objects.create_user(username='business')
        self.offer = Offer.objects.create(
            user=self.business,
            title='Logo Offer',
            description='Offer description',
        )
        self.detail = self._create_offer_detail()
        self.order = self._create_order()

    def test_order_serializer_fields_are_exact(self):
        serializer = OrderSerializer(self.order)
        self.assertEqual(set(serializer.data.keys()), {
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
        })

    def test_order_serializer_returns_correct_values(self):
        serializer = OrderSerializer(self.order)
        self.assertEqual(serializer.data['title'], 'Logo Design')
        self.assertEqual(serializer.data['revisions'], 2)
        self.assertEqual(serializer.data['delivery_time_in_days'], 5)
        self.assertEqual(serializer.data['price'], '99.99')

    def test_customer_user_is_serialized_as_user_id(self):
        serializer = OrderSerializer(self.order)
        self.assertEqual(serializer.data['customer_user'], self.customer.id)

    def test_business_user_is_serialized_as_user_id(self):
        serializer = OrderSerializer(self.order)
        self.assertEqual(serializer.data['business_user'], self.business.id)

    def test_features_are_returned_as_list(self):
        serializer = OrderSerializer(self.order)
        self.assertEqual(serializer.data['features'], ['Logo', 'Source file'])

    def test_timestamps_are_included(self):
        serializer = OrderSerializer(self.order)
        self.assertIn('created_at', serializer.data)
        self.assertIn('updated_at', serializer.data)

    def test_create_serializer_accepts_valid_offer_detail_id(self):
        serializer = OrderCreateSerializer(
            data={'offer_detail_id': self.detail.id},
        )
        self.assertTrue(serializer.is_valid())

    def test_create_serializer_rejects_missing_offer_detail_id(self):
        serializer = OrderCreateSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('offer_detail_id', serializer.errors)

    def test_create_serializer_rejects_malformed_offer_detail_id(self):
        serializer = OrderCreateSerializer(data={'offer_detail_id': 'abc'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('offer_detail_id', serializer.errors)

    def test_create_serializer_does_not_require_snapshot_fields(self):
        serializer = OrderCreateSerializer(
            data={'offer_detail_id': self.detail.id},
        )
        self.assertTrue(serializer.is_valid())

    def test_snapshot_customer_user_comes_from_save_context(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.customer_user, self.customer)

    def test_snapshot_business_user_comes_from_offer_detail_offer_user(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.business_user, self.business)

    def test_snapshot_title_is_copied(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.title, self.detail.title)

    def test_snapshot_revisions_are_copied(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.revisions, self.detail.revisions)

    def test_snapshot_delivery_time_is_copied(self):
        order = self._create_order_from_detail()
        self.assertEqual(
            order.delivery_time_in_days,
            self.detail.delivery_time_in_days,
        )

    def test_snapshot_price_is_copied(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.price, self.detail.price)

    def test_snapshot_features_are_copied(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.features, self.detail.features)

    def test_snapshot_offer_type_is_copied(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.offer_type, self.detail.offer_type)

    def test_snapshot_status_defaults_to_in_progress(self):
        order = self._create_order_from_detail()
        self.assertEqual(order.status, Order.IN_PROGRESS)

    def test_editing_offer_detail_does_not_change_order_snapshot(self):
        order = self._create_order_from_detail()
        self.detail.title = 'Changed'
        self.detail.price = Decimal('199.99')
        self.detail.save()
        order.refresh_from_db()
        self.assertEqual(order.title, 'Basic Package')
        self.assertEqual(order.price, Decimal('99.99'))

    def test_order_features_are_independent_of_offer_detail_changes(self):
        order = self._create_order_from_detail()
        self.detail.features.append('Later feature')
        self.detail.save()
        order.refresh_from_db()
        self.assertEqual(order.features, ['Logo', 'Source file'])

    def test_status_update_accepts_in_progress(self):
        serializer = self._status_serializer(Order.IN_PROGRESS)
        self.assertTrue(serializer.is_valid())

    def test_status_update_accepts_completed(self):
        serializer = self._status_serializer(Order.COMPLETED)
        self.assertTrue(serializer.is_valid())

    def test_status_update_accepts_cancelled(self):
        serializer = self._status_serializer(Order.CANCELLED)
        self.assertTrue(serializer.is_valid())

    def test_status_update_rejects_invalid_status(self):
        serializer = self._status_serializer('invalid')
        self.assertFalse(serializer.is_valid())
        self.assertIn('status', serializer.errors)

    def test_status_update_rejects_title_field(self):
        serializer = OrderStatusUpdateSerializer(data={'title': 'Changed'})
        self.assertFalse(serializer.is_valid())

    def test_status_update_rejects_price_field(self):
        serializer = OrderStatusUpdateSerializer(data={'price': '1.00'})
        self.assertFalse(serializer.is_valid())

    def test_status_update_rejects_mixed_forbidden_field(self):
        serializer = OrderStatusUpdateSerializer(
            data={'status': Order.COMPLETED, 'price': '1.00'},
        )
        self.assertFalse(serializer.is_valid())

    def _status_serializer(self, status):
        return OrderStatusUpdateSerializer(data={'status': status})

    def _create_order_from_detail(self):
        serializer = OrderCreateSerializer(
            data={'offer_detail_id': self.detail.id},
        )
        serializer.is_valid()
        return serializer.save(
            customer_user=self.customer,
            offer_detail=self.detail,
        )

    def _create_order(self):
        return Order.objects.create(
            customer_user=self.customer,
            business_user=self.business,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
        )

    def _create_offer_detail(self):
        return OfferDetail.objects.create(
            offer=self.offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=OfferDetail.BASIC,
        )


class OrderCreateViewTests(APITestCase):
    """Tests for the customer-only order creation endpoint."""

    def setUp(self):
        self.url = reverse('orders_app:order-create')
        self.customer = User.objects.create_user(username='customer')
        self.business = User.objects.create_user(username='business')
        self.no_profile_user = User.objects.create_user(username='noProfile')
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business, type=Profile.BUSINESS)
        self.offer = Offer.objects.create(
            user=self.business,
            title='Logo Offer',
            description='Offer description',
        )
        self.detail = self._create_offer_detail()

    def test_authenticated_customer_creates_order(self):
        response = self._post_as_customer()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_order_row_is_created(self):
        self._post_as_customer()
        self.assertEqual(Order.objects.count(), 1)

    def test_response_field_set_is_exact(self):
        response = self._post_as_customer()
        self.assertEqual(set(response.data.keys()), {
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
        })

    def test_customer_user_is_request_user_id(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['customer_user'], self.customer.id)

    def test_business_user_is_offer_detail_offer_user_id(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['business_user'], self.business.id)

    def test_title_is_copied(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['title'], self.detail.title)

    def test_revisions_are_copied(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['revisions'], self.detail.revisions)

    def test_delivery_time_in_days_is_copied(self):
        response = self._post_as_customer()
        self.assertEqual(
            response.data['delivery_time_in_days'],
            self.detail.delivery_time_in_days,
        )

    def test_price_is_copied(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['price'], '99.99')

    def test_features_are_copied(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['features'], self.detail.features)

    def test_offer_type_is_copied(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['offer_type'], self.detail.offer_type)

    def test_status_defaults_to_in_progress(self):
        response = self._post_as_customer()
        self.assertEqual(response.data['status'], Order.IN_PROGRESS)

    def test_timestamps_are_present(self):
        response = self._post_as_customer()
        self.assertTrue(response.data['created_at'])
        self.assertTrue(response.data['updated_at'])

    def test_offer_detail_id_is_not_in_response(self):
        response = self._post_as_customer()
        self.assertNotIn('offer_detail_id', response.data)

    def test_unauthenticated_returns_unauthorized(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_user_returns_forbidden(self):
        self.client.force_authenticate(user=self.business)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_without_profile_returns_forbidden(self):
        self.client.force_authenticate(user=self.no_profile_user)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_offer_detail_id_returns_bad_request(self):
        response = self._post_as_customer({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_offer_detail_id_returns_bad_request(self):
        response = self._post_as_customer({'offer_detail_id': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_offer_detail_id_returns_not_found(self):
        response = self._post_as_customer({'offer_detail_id': 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_cannot_select_customer_user(self):
        payload = self._payload(customer_user=self.no_profile_user.id)
        response = self._post_as_customer(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_select_business_user(self):
        payload = self._payload(business_user=self.no_profile_user.id)
        response = self._post_as_customer(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_override_price(self):
        response = self._post_as_customer(self._payload(price='1.00'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_override_status(self):
        response = self._post_as_customer(self._payload(status=Order.COMPLETED))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_snapshot_values_remain_after_offer_detail_changes(self):
        self._post_as_customer()
        order = Order.objects.get()
        self.detail.title = 'Changed title'
        self.detail.price = Decimal('199.99')
        self.detail.features = ['Changed']
        self.detail.save()
        order.refresh_from_db()
        self.assertEqual(order.title, 'Basic Package')
        self.assertEqual(order.price, Decimal('99.99'))
        self.assertEqual(order.features, ['Logo', 'Source file'])

    def _post_as_customer(self, payload=None):
        self.client.force_authenticate(user=self.customer)
        if payload is None:
            payload = self._payload()
        return self.client.post(self.url, payload, format='json')

    def _payload(self, **extra):
        payload = {'offer_detail_id': self.detail.id}
        payload.update(extra)
        return payload

    def _create_offer_detail(self):
        return OfferDetail.objects.create(
            offer=self.offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=OfferDetail.BASIC,
        )


class OrderListViewTests(APITestCase):
    """Tests for the authenticated order list endpoint."""

    def setUp(self):
        self.url = reverse('orders_app:order-create')
        self.customer = User.objects.create_user(username='customer')
        self.business = User.objects.create_user(username='business')
        self.other_user = User.objects.create_user(username='other')
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business, type=Profile.BUSINESS)
        Profile.objects.create(user=self.other_user, type=Profile.CUSTOMER)

    def test_authenticated_customer_gets_ok(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_business_gets_ok(self):
        self.client.force_authenticate(user=self.business)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_gets_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_sees_order_as_customer_user(self):
        order = self._create_order(self.customer, self.business)
        response = self._get_as(self.customer)
        self.assertEqual(self._result_ids(response), [order.id])

    def test_business_sees_order_as_business_user(self):
        order = self._create_order(self.customer, self.business)
        response = self._get_as(self.business)
        self.assertEqual(self._result_ids(response), [order.id])

    def test_user_sees_orders_in_either_role(self):
        first = self._create_order(self.customer, self.business)
        second = self._create_order(self.other_user, self.customer)
        response = self._get_as(self.customer)
        self.assertEqual(set(self._result_ids(response)), {first.id, second.id})

    def test_unrelated_order_is_excluded(self):
        self._create_order(self.other_user, self.business)
        response = self._get_as(self.customer)
        self.assertEqual(response.data, [])

    def test_several_matching_orders_are_returned(self):
        first = self._create_order(self.customer, self.business)
        second = self._create_order(self.customer, self.other_user)
        response = self._get_as(self.customer)
        self.assertEqual(set(self._result_ids(response)), {first.id, second.id})

    def test_empty_matching_set_returns_empty_list(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data, [])

    def test_no_unrelated_data_leakage(self):
        unrelated = self._create_order(self.other_user, self.business)
        response = self._get_as(self.customer)
        self.assertNotIn(unrelated.id, self._result_ids(response))

    def test_response_is_list(self):
        response = self._get_as(self.customer)
        self.assertIsInstance(response.data, list)

    def test_response_field_set_is_exact(self):
        self._create_order(self.customer, self.business)
        response = self._get_as(self.customer)
        self.assertEqual(set(response.data[0].keys()), {
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
        })

    def test_values_match_stored_snapshot(self):
        order = self._create_order(self.customer, self.business)
        response = self._get_as(self.customer)
        self.assertEqual(response.data[0]['title'], order.title)
        self.assertEqual(response.data[0]['price'], '99.99')
        self.assertEqual(response.data[0]['features'], order.features)

    def test_post_customer_still_returns_created(self):
        detail = self._create_offer_detail()
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            self.url,
            {'offer_detail_id': detail.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_post_business_still_returns_forbidden(self):
        detail = self._create_offer_detail()
        self.client.force_authenticate(user=self.business)
        response = self.client.post(
            self.url,
            {'offer_detail_id': detail.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_missing_offer_detail_id_still_returns_bad_request(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_nonexistent_offer_detail_still_returns_not_found(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            self.url,
            {'offer_detail_id': 999},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def _get_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.get(self.url)

    def _result_ids(self, response):
        return [order['id'] for order in response.data]

    def _create_order(self, customer_user, business_user):
        return Order.objects.create(
            customer_user=customer_user,
            business_user=business_user,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
        )

    def _create_offer_detail(self):
        offer = Offer.objects.create(
            user=self.business,
            title='Logo Offer',
            description='Offer description',
        )
        return OfferDetail.objects.create(
            offer=offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=OfferDetail.BASIC,
        )


class OrderStatusUpdateViewTests(APITestCase):
    """Tests for the business-owner order status PATCH endpoint."""

    def setUp(self):
        self.customer = User.objects.create_user(username='customer')
        self.other_customer = User.objects.create_user(username='otherCustomer')
        self.business = User.objects.create_user(username='business')
        self.other_business = User.objects.create_user(username='otherBusiness')
        self.no_profile_user = User.objects.create_user(username='noProfile')
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.other_customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business, type=Profile.BUSINESS)
        Profile.objects.create(user=self.other_business, type=Profile.BUSINESS)
        self.order = self._create_order()
        self.url = reverse('orders_app:order-detail', kwargs={'pk': self.order.id})

    def test_owning_business_user_can_patch(self):
        response = self._patch_as_business({'status': Order.COMPLETED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_in_progress_can_change_to_completed(self):
        self._patch_as_business({'status': Order.COMPLETED})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.COMPLETED)

    def test_in_progress_can_change_to_cancelled(self):
        self._patch_as_business({'status': Order.CANCELLED})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.CANCELLED)

    def test_completed_can_change_to_in_progress(self):
        self.order.status = Order.COMPLETED
        self.order.save()
        self._patch_as_business({'status': Order.IN_PROGRESS})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.IN_PROGRESS)

    def test_response_field_set_is_exact(self):
        response = self._patch_as_business({'status': Order.COMPLETED})
        self.assertEqual(set(response.data.keys()), {
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
        })

    def test_status_is_persisted(self):
        self._patch_as_business({'status': Order.CANCELLED})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.CANCELLED)

    def test_updated_at_changes(self):
        original_updated_at = self.order.updated_at
        self._patch_as_business({'status': Order.COMPLETED})
        self.order.refresh_from_db()
        self.assertGreater(self.order.updated_at, original_updated_at)

    def test_unauthenticated_gets_unauthorized(self):
        response = self.client.patch(self.url, {'status': Order.COMPLETED})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_user_gets_forbidden(self):
        response = self._patch_as(self.customer, {'status': Order.COMPLETED})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_customer_gets_forbidden(self):
        response = self._patch_as(
            self.other_customer,
            {'status': Order.COMPLETED},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_different_business_user_gets_forbidden(self):
        response = self._patch_as(
            self.other_business,
            {'status': Order.COMPLETED},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_without_profile_gets_forbidden(self):
        self.order.business_user = self.no_profile_user
        self.order.save()
        response = self._patch_as(
            self.no_profile_user,
            {'status': Order.COMPLETED},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_status_returns_bad_request(self):
        response = self._patch_as_business({'status': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_title_field_returns_bad_request(self):
        response = self._patch_as_business({'title': 'Changed'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_price_field_returns_bad_request(self):
        response = self._patch_as_business({'price': '1.00'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_user_field_returns_bad_request(self):
        response = self._patch_as_business({'customer_user': self.other_customer.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_business_user_field_returns_bad_request(self):
        response = self._patch_as_business({'business_user': self.other_business.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_features_field_returns_bad_request(self):
        response = self._patch_as_business({'features': ['Changed']})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_with_forbidden_field_returns_bad_request(self):
        response = self._patch_as_business({
            'status': Order.COMPLETED,
            'price': '1.00',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_patch_returns_bad_request(self):
        response = self._patch_as_business({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_immutable_fields_remain_unchanged(self):
        original = self._snapshot()
        self._patch_as_business({'status': Order.COMPLETED})
        self.order.refresh_from_db()
        self.assertEqual(self._snapshot(), original)

    def test_nonexistent_order_returns_not_found(self):
        self.client.force_authenticate(user=self.business)
        response = self.client.patch(
            reverse('orders_app:order-detail', kwargs={'pk': 999}),
            {'status': Order.COMPLETED},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_orders_list_still_works(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('orders_app:order-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_orders_still_works(self):
        offer_detail = self._create_offer_detail()
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            reverse('orders_app:order-create'),
            {'offer_detail_id': offer_detail.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_detail_get_is_not_exposed(self):
        self.client.force_authenticate(user=self.business)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_detail_put_is_not_exposed(self):
        self.client.force_authenticate(user=self.business)
        response = self.client.put(self.url, {'status': Order.COMPLETED})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def _patch_as_business(self, payload):
        return self._patch_as(self.business, payload)

    def _patch_as(self, user, payload):
        self.client.force_authenticate(user=user)
        return self.client.patch(self.url, payload, format='json')

    def _snapshot(self):
        return {
            'customer_user': self.order.customer_user,
            'business_user': self.order.business_user,
            'title': self.order.title,
            'revisions': self.order.revisions,
            'delivery_time_in_days': self.order.delivery_time_in_days,
            'price': self.order.price,
            'features': self.order.features,
            'offer_type': self.order.offer_type,
            'created_at': self.order.created_at,
        }

    def _create_order(self):
        return Order.objects.create(
            customer_user=self.customer,
            business_user=self.business,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
        )

    def _create_offer_detail(self):
        offer = Offer.objects.create(
            user=self.business,
            title='Logo Offer',
            description='Offer description',
        )
        return OfferDetail.objects.create(
            offer=offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=OfferDetail.BASIC,
        )


class OrderDeleteViewTests(APITestCase):
    """Tests for the staff-only order DELETE endpoint."""

    def setUp(self):
        self.customer = User.objects.create_user(username='customer')
        self.business = User.objects.create_user(username='business')
        self.other_business = User.objects.create_user(username='otherBusiness')
        self.no_profile_user = User.objects.create_user(username='noProfile')
        self.staff_user = User.objects.create_user('staff', is_staff=True)
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business, type=Profile.BUSINESS)
        Profile.objects.create(user=self.other_business, type=Profile.BUSINESS)
        self.offer = Offer.objects.create(
            user=self.business,
            title='Logo Offer',
            description='Offer description',
        )
        self.offer_detail = self._create_offer_detail()
        self.order = self._create_order()
        self.url = reverse('orders_app:order-detail', kwargs={'pk': self.order.id})

    def test_staff_user_can_delete(self):
        response = self._delete_as(self.staff_user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_response_body_is_empty(self):
        response = self._delete_as(self.staff_user)
        self.assertIsNone(response.data)

    def test_order_removed_from_database(self):
        self._delete_as(self.staff_user)
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())

    def test_staff_customer_profile_may_delete(self):
        user = self._staff_with_profile('staffCustomer', Profile.CUSTOMER)
        response = self._delete_as(user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_business_profile_may_delete(self):
        user = self._staff_with_profile('staffBusiness', Profile.BUSINESS)
        response = self._delete_as(user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_user_without_profile_may_delete(self):
        response = self._delete_as(self.staff_user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_staff_customer_gets_forbidden(self):
        response = self._delete_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_business_gets_forbidden(self):
        response = self._delete_as(self.other_business)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_customer_gets_forbidden(self):
        response = self._delete_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_business_user_gets_forbidden_if_not_staff(self):
        response = self._delete_as(self.business)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_profile_user_gets_forbidden(self):
        response = self._delete_as(self.no_profile_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gets_unauthorized(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_deleting_nonexistent_order_gets_not_found(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(
            reverse('orders_app:order-detail', kwargs={'pk': 999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owning_business_user_can_still_patch(self):
        self.client.force_authenticate(user=self.business)
        response = self.client.patch(
            self.url,
            {'status': Order.COMPLETED},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unrelated_business_cannot_patch(self):
        self.client.force_authenticate(user=self.other_business)
        response = self.client.patch(
            self.url,
            {'status': Order.COMPLETED},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_staff_cannot_patch_because_staff(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.patch(
            self.url,
            {'status': Order.COMPLETED},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_detail_is_not_exposed(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_detail_is_not_exposed(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.put(self.url, {'status': Order.COMPLETED})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_orders_list_still_works(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('orders_app:order-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_orders_still_works(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            reverse('orders_app:order-create'),
            {'offer_detail_id': self.offer_detail.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_does_not_remove_offer_or_offer_detail(self):
        self._delete_as(self.staff_user)
        self.assertTrue(Offer.objects.filter(pk=self.offer.pk).exists())
        self.assertTrue(OfferDetail.objects.filter(pk=self.offer_detail.pk).exists())

    def _delete_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.delete(self.url)

    def _staff_with_profile(self, username, profile_type):
        user = User.objects.create_user(username=username, is_staff=True)
        Profile.objects.create(user=user, type=profile_type)
        return user

    def _create_order(self):
        return Order.objects.create(
            customer_user=self.customer,
            business_user=self.business,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
        )

    def _create_offer_detail(self):
        return OfferDetail.objects.create(
            offer=self.offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=OfferDetail.BASIC,
        )


class OrderCountViewTests(APITestCase):
    """Tests for the in-progress order count endpoint."""

    def setUp(self):
        self.customer = User.objects.create_user(username='customer')
        self.business_a = User.objects.create_user(username='businessA')
        self.business_b = User.objects.create_user(username='businessB')
        self.no_profile_user = User.objects.create_user(username='noProfile')
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business_a, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_b, type=Profile.BUSINESS)
        self._create_order_data()
        self.url = reverse(
            'orders_app:order-count',
            kwargs={'business_user_id': self.business_a.id},
        )

    def test_authenticated_customer_can_call_endpoint(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_business_can_call_endpoint(self):
        response = self._get_as(self.business_b)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_business_user_returns_ok(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_field_set_is_exact(self):
        response = self._get_as(self.customer)
        self.assertEqual(set(response.data.keys()), {'order_count'})

    def test_correct_integer_count_is_returned(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data['order_count'], 2)
        self.assertIsInstance(response.data['order_count'], int)

    def test_counts_in_progress_only(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data, {'order_count': 2})

    def test_completed_orders_are_excluded(self):
        response = self._get_as(self.customer)
        self.assertNotEqual(response.data['order_count'], 3)

    def test_cancelled_orders_are_excluded(self):
        response = self._get_as(self.customer)
        self.assertNotEqual(response.data['order_count'], 3)

    def test_other_business_orders_are_excluded(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data['order_count'], 2)

    def test_zero_in_progress_orders_returns_zero(self):
        Order.objects.filter(business_user=self.business_a).update(
            status=Order.COMPLETED,
        )
        response = self._get_as(self.customer)
        self.assertEqual(response.data, {'order_count': 0})

    def test_nonexistent_user_returns_not_found(self):
        response = self._get_as(
            self.customer,
            reverse('orders_app:order-count', kwargs={'business_user_id': 999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_user_returns_not_found(self):
        url = reverse(
            'orders_app:order-count',
            kwargs={'business_user_id': self.customer.id},
        )
        response = self._get_as(self.business_a, url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_profile_returns_not_found(self):
        url = reverse(
            'orders_app:order-count',
            kwargs={'business_user_id': self.no_profile_user.id},
        )
        response = self._get_as(self.customer, url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_orders_list_still_works(self):
        response = self._get_as(self.customer, reverse('orders_app:order-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_orders_still_works(self):
        detail = self._create_offer_detail(self.business_a)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            reverse('orders_app:order-create'),
            {'offer_detail_id': detail.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_patch_orders_still_works(self):
        order = Order.objects.filter(business_user=self.business_a).first()
        self.client.force_authenticate(user=self.business_a)
        response = self.client.patch(
            reverse('orders_app:order-detail', kwargs={'pk': order.id}),
            {'status': Order.COMPLETED},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_orders_still_works(self):
        staff = User.objects.create_user(username='staff', is_staff=True)
        order = Order.objects.filter(business_user=self.business_a).first()
        self.client.force_authenticate(user=staff)
        response = self.client.delete(
            reverse('orders_app:order-detail', kwargs={'pk': order.id}),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def _get_as(self, user, url=None):
        self.client.force_authenticate(user=user)
        return self.client.get(url or self.url)

    def _create_order_data(self):
        self._create_order(self.business_a, Order.IN_PROGRESS)
        self._create_order(self.business_a, Order.IN_PROGRESS)
        self._create_order(self.business_a, Order.COMPLETED)
        self._create_order(self.business_a, Order.CANCELLED)
        self._create_order(self.business_b, Order.IN_PROGRESS)

    def _create_order(self, business_user, order_status):
        return Order.objects.create(
            customer_user=self.customer,
            business_user=business_user,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
            status=order_status,
        )

    def _create_offer_detail(self, business_user):
        offer = Offer.objects.create(
            user=business_user,
            title='Logo Offer',
            description='Offer description',
        )
        return OfferDetail.objects.create(
            offer=offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=OfferDetail.BASIC,
        )


class CompletedOrderCountViewTests(APITestCase):
    """Tests for the completed order count endpoint."""

    def setUp(self):
        self.customer = User.objects.create_user(username='customerCompleted')
        self.business_a = User.objects.create_user(username='businessDoneA')
        self.business_b = User.objects.create_user(username='businessDoneB')
        self.no_profile_user = User.objects.create_user(username='noDoneProfile')
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business_a, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_b, type=Profile.BUSINESS)
        self._create_order_data()
        self.url = reverse(
            'orders_app:completed-order-count',
            kwargs={'business_user_id': self.business_a.id},
        )

    def test_authenticated_customer_can_call_endpoint(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_business_can_call_endpoint(self):
        response = self._get_as(self.business_b)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_business_user_returns_ok(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_field_set_is_exact(self):
        response = self._get_as(self.customer)
        self.assertEqual(set(response.data.keys()), {'completed_order_count'})

    def test_correct_integer_count_is_returned(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data['completed_order_count'], 2)
        self.assertIsInstance(response.data['completed_order_count'], int)

    def test_counts_completed_only(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data, {'completed_order_count': 2})

    def test_in_progress_orders_are_excluded(self):
        response = self._get_as(self.customer)
        self.assertNotEqual(response.data['completed_order_count'], 3)

    def test_cancelled_orders_are_excluded(self):
        response = self._get_as(self.customer)
        self.assertNotEqual(response.data['completed_order_count'], 3)

    def test_other_business_orders_are_excluded(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.data['completed_order_count'], 2)

    def test_zero_completed_orders_returns_zero(self):
        Order.objects.filter(business_user=self.business_a).update(
            status=Order.IN_PROGRESS,
        )
        response = self._get_as(self.customer)
        self.assertEqual(response.data, {'completed_order_count': 0})

    def test_nonexistent_user_returns_not_found(self):
        response = self._get_as(
            self.customer,
            reverse(
                'orders_app:completed-order-count',
                kwargs={'business_user_id': 999},
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_user_returns_not_found(self):
        url = reverse(
            'orders_app:completed-order-count',
            kwargs={'business_user_id': self.customer.id},
        )
        response = self._get_as(self.business_a, url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_profile_returns_not_found(self):
        url = reverse(
            'orders_app:completed-order-count',
            kwargs={'business_user_id': self.no_profile_user.id},
        )
        response = self._get_as(self.customer, url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_orders_list_still_works(self):
        response = self._get_as(self.customer, reverse('orders_app:order-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_orders_detail_still_works(self):
        order = Order.objects.filter(business_user=self.business_a).first()
        self.client.force_authenticate(user=self.business_a)
        response = self.client.patch(
            reverse('orders_app:order-detail', kwargs={'pk': order.id}),
            {'status': Order.COMPLETED},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_order_count_endpoint_still_works(self):
        url = reverse(
            'orders_app:order-count',
            kwargs={'business_user_id': self.business_a.id},
        )
        response = self._get_as(self.customer, url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def _get_as(self, user, url=None):
        self.client.force_authenticate(user=user)
        return self.client.get(url or self.url)

    def _create_order_data(self):
        self._create_order(self.business_a, Order.COMPLETED)
        self._create_order(self.business_a, Order.COMPLETED)
        self._create_order(self.business_a, Order.IN_PROGRESS)
        self._create_order(self.business_a, Order.CANCELLED)
        self._create_order(self.business_b, Order.COMPLETED)

    def _create_order(self, business_user, order_status):
        return Order.objects.create(
            customer_user=self.customer,
            business_user=business_user,
            title='Logo Design',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo', 'Source file'],
            offer_type=Order.BASIC,
            status=order_status,
        )

