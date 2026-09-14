from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from offers_app.api.serializers import (
    OfferDetailLinkSerializer,
    OfferDetailSerializer,
    OfferListSerializer,
    OfferRetrieveSerializer,
    OfferWriteResponseSerializer,
    OfferWriteSerializer,
)
from offers_app.models import Offer, OfferDetail
from profile_app.models import Profile


User = get_user_model()


class OfferModelTests(TestCase):
    """Tests for offer data models."""

    def setUp(self):
        self.user = User.objects.create_user(username='businessUser')
        self.offer = Offer.objects.create(
            user=self.user,
            title='Logo Design',
            description='Professional logo design package',
        )

    def test_offer_can_be_created(self):
        self.assertEqual(Offer.objects.count(), 1)
        self.assertEqual(self.offer.title, 'Logo Design')

    def test_offer_detail_can_be_created(self):
        detail = self._create_detail(OfferDetail.BASIC)
        self.assertEqual(OfferDetail.objects.count(), 1)
        self.assertEqual(detail.offer_type, OfferDetail.BASIC)

    def test_offer_belongs_to_correct_user(self):
        self.assertEqual(self.offer.user, self.user)

    def test_offer_detail_belongs_to_correct_offer(self):
        detail = self._create_detail(OfferDetail.STANDARD)
        self.assertEqual(detail.offer, self.offer)

    def test_offer_details_relation_works(self):
        detail = self._create_detail(OfferDetail.PREMIUM)
        self.assertEqual(list(self.offer.details.all()), [detail])

    def test_basic_standard_premium_offer_types_are_supported(self):
        choices = dict(OfferDetail.OFFER_TYPE_CHOICES)
        self.assertIn(OfferDetail.BASIC, choices)
        self.assertIn(OfferDetail.STANDARD, choices)
        self.assertIn(OfferDetail.PREMIUM, choices)

    def test_deleting_offer_deletes_details(self):
        self._create_detail(OfferDetail.BASIC)
        self.offer.delete()
        self.assertEqual(OfferDetail.objects.count(), 0)

    def test_offer_str_returns_readable_value(self):
        self.assertEqual(str(self.offer), 'Logo Design')

    def test_offer_detail_str_returns_readable_value(self):
        detail = self._create_detail(OfferDetail.BASIC)
        self.assertEqual(str(detail), 'Logo Design - Basic Package')

    def test_created_at_is_populated(self):
        self.assertIsNotNone(self.offer.created_at)

    def test_updated_at_is_populated(self):
        self.assertIsNotNone(self.offer.updated_at)

    def test_features_can_store_list_of_strings(self):
        detail = self._create_detail(OfferDetail.BASIC)
        detail.refresh_from_db()
        self.assertEqual(detail.features, ['Logo draft', 'Source file'])

    def _create_detail(self, offer_type):
        return OfferDetail.objects.create(
            offer=self.offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('99.99'),
            features=['Logo draft', 'Source file'],
            offer_type=offer_type,
        )


class OfferSerializerTests(TestCase):
    """Tests for offer API serializers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='businessUser',
            first_name='Business',
            last_name='User',
        )
        self.offer = Offer.objects.create(
            user=self.user,
            title='Logo Design',
            description='Professional logo design package',
        )

    def test_detail_serializer_fields_are_exact(self):
        detail = self._create_detail(OfferDetail.BASIC)
        serializer = OfferDetailSerializer(detail)
        self.assertEqual(set(serializer.data.keys()), {
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        })

    def test_detail_serializer_accepts_valid_detail(self):
        serializer = OfferDetailSerializer(data=self._detail_data())
        self.assertTrue(serializer.is_valid())

    def test_detail_serializer_features_list_works(self):
        serializer = OfferDetailSerializer(data=self._detail_data())
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['features'], ['A', 'B'])

    def test_detail_serializer_rejects_invalid_feature_type(self):
        data = self._detail_data(features=['A', 5])
        serializer = OfferDetailSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('features', serializer.errors)

    def test_detail_serializer_rejects_invalid_offer_type(self):
        data = self._detail_data(offer_type='gold')
        serializer = OfferDetailSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('offer_type', serializer.errors)

    def test_write_serializer_creates_valid_offer(self):
        serializer = OfferWriteSerializer(data=self._offer_data())
        self.assertTrue(serializer.is_valid())
        offer = serializer.save(user=self.user)
        self.assertEqual(offer.title, 'Website Design')

    def test_write_serializer_creates_exactly_three_details(self):
        serializer = OfferWriteSerializer(data=self._offer_data())
        serializer.is_valid()
        offer = serializer.save(user=self.user)
        self.assertEqual(offer.details.count(), 3)

    def test_created_details_belong_to_created_offer(self):
        serializer = OfferWriteSerializer(data=self._offer_data())
        serializer.is_valid()
        offer = serializer.save(user=self.user)
        self.assertEqual(offer.details.filter(offer=offer).count(), 3)

    def test_write_serializer_rejects_fewer_than_three_details(self):
        data = self._offer_data(details=self._detail_list()[:2])
        serializer = OfferWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('details', serializer.errors)

    def test_write_serializer_rejects_more_than_three_details(self):
        details = self._detail_list() + [self._detail_data()]
        serializer = OfferWriteSerializer(data=self._offer_data(details))
        self.assertFalse(serializer.is_valid())
        self.assertIn('details', serializer.errors)

    def test_write_serializer_rejects_duplicate_offer_type(self):
        details = self._detail_list()
        details[1]['offer_type'] = OfferDetail.BASIC
        serializer = OfferWriteSerializer(data=self._offer_data(details))
        self.assertFalse(serializer.is_valid())
        self.assertIn('details', serializer.errors)

    def test_write_serializer_rejects_missing_package_type(self):
        details = self._detail_list()
        details[2]['offer_type'] = OfferDetail.STANDARD
        serializer = OfferWriteSerializer(data=self._offer_data(details))
        self.assertFalse(serializer.is_valid())
        self.assertIn('details', serializer.errors)

    def test_list_serializer_fields_are_exact(self):
        serializer = OfferListSerializer(self.offer)
        self.assertEqual(set(serializer.data.keys()), {
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
        })

    def test_retrieve_serializer_fields_are_exact(self):
        serializer = OfferRetrieveSerializer(self.offer)
        self.assertEqual(set(serializer.data.keys()), {
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
        })

    def test_write_response_serializer_fields_are_exact(self):
        self._create_detail(OfferDetail.BASIC)
        serializer = OfferWriteResponseSerializer(self.offer)
        self.assertEqual(set(serializer.data.keys()), {
            'id',
            'title',
            'image',
            'description',
            'details',
        })

    def test_min_price_returns_lowest_detail_price(self):
        self._create_detail(OfferDetail.BASIC, price=Decimal('80.00'))
        self._create_detail(OfferDetail.PREMIUM, price=Decimal('120.00'))
        serializer = OfferListSerializer(self.offer)
        self.assertEqual(serializer.data['min_price'], Decimal('80.00'))

    def test_min_delivery_time_returns_shortest_time(self):
        self._create_detail(OfferDetail.BASIC, delivery_time=4)
        self._create_detail(OfferDetail.PREMIUM, delivery_time=7)
        serializer = OfferListSerializer(self.offer)
        self.assertEqual(serializer.data['min_delivery_time'], 4)

    def test_user_details_contains_exact_fields(self):
        serializer = OfferListSerializer(self.offer)
        self.assertEqual(set(serializer.data['user_details'].keys()), {
            'first_name',
            'last_name',
            'username',
        })

    def test_compact_detail_contains_only_id_and_url(self):
        detail = self._create_detail(OfferDetail.BASIC)
        serializer = OfferDetailLinkSerializer(detail)
        self.assertEqual(set(serializer.data.keys()), {'id', 'url'})

    def test_compact_detail_url_points_to_offer_detail_endpoint(self):
        detail = self._create_detail(OfferDetail.BASIC)
        request = APIRequestFactory().get('/')
        serializer = OfferDetailLinkSerializer(
            detail,
            context={'request': request},
        )
        self.assertIn(f'/api/offerdetails/{detail.id}/', serializer.data['url'])

    def test_partial_offer_update_leaves_omitted_fields_unchanged(self):
        serializer = OfferWriteSerializer(
            self.offer,
            data={'title': 'Updated'},
            partial=True,
        )
        serializer.is_valid()
        serializer.save()
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.description, 'Professional logo design package')

    def test_one_detail_can_be_updated_by_offer_type(self):
        detail = self._create_detail(OfferDetail.BASIC)
        self._patch_offer_detail({'title': 'Updated Basic'})
        detail.refresh_from_db()
        self.assertEqual(detail.title, 'Updated Basic')

    def test_other_details_stay_unchanged(self):
        self._create_detail(OfferDetail.BASIC)
        standard = self._create_detail(OfferDetail.STANDARD)
        self._patch_offer_detail({'title': 'Updated Basic'})
        standard.refresh_from_db()
        self.assertEqual(standard.title, 'Standard Package')

    def test_updated_detail_keeps_same_database_id(self):
        detail = self._create_detail(OfferDetail.BASIC)
        self._patch_offer_detail({'title': 'Updated Basic'})
        detail.refresh_from_db()
        self.assertEqual(detail.id, self.offer.details.get(offer_type='basic').id)

    def test_partial_detail_update_does_not_require_all_details(self):
        response = self._patch_offer_detail({'title': 'Updated Basic'})
        self.assertEqual(response.title, 'Logo Design')

    def test_unknown_detail_type_is_not_created_on_update(self):
        serializer = OfferWriteSerializer(
            self.offer,
            data={'details': [self._detail_data(offer_type='premium')]},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('details', serializer.errors)

    def _patch_offer_detail(self, detail_data):
        self._create_detail_if_missing(OfferDetail.BASIC)
        detail_data['offer_type'] = OfferDetail.BASIC
        serializer = OfferWriteSerializer(
            self.offer,
            data={'details': [detail_data]},
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        return serializer.save()

    def _create_detail_if_missing(self, offer_type):
        if not self.offer.details.filter(offer_type=offer_type).exists():
            self._create_detail(offer_type)

    def _offer_data(self, details=None):
        return {
            'title': 'Website Design',
            'description': 'Modern landing page',
            'details': details or self._detail_list(),
        }

    def _detail_list(self):
        return [
            self._detail_data(offer_type=OfferDetail.BASIC),
            self._detail_data(offer_type=OfferDetail.STANDARD),
            self._detail_data(offer_type=OfferDetail.PREMIUM),
        ]

    def _detail_data(self, offer_type=OfferDetail.BASIC, features=None):
        return {
            'title': 'Basic Package',
            'revisions': 2,
            'delivery_time_in_days': 5,
            'price': '99.99',
            'features': features or ['A', 'B'],
            'offer_type': offer_type,
        }

    def _create_detail(
        self,
        offer_type,
        price=Decimal('99.99'),
        delivery_time=5,
    ):
        title = f'{offer_type.title()} Package'
        return OfferDetail.objects.create(
            offer=self.offer,
            title=title,
            revisions=2,
            delivery_time_in_days=delivery_time,
            price=price,
            features=['A', 'B'],
            offer_type=offer_type,
        )


class OfferCreateViewTests(APITestCase):
    """Tests for the offer creation endpoint."""

    def setUp(self):
        self.url = reverse('offers_app:offer-create')
        self.business_user = User.objects.create_user(username='businessUser')
        self.customer_user = User.objects.create_user(username='customerUser')
        Profile.objects.create(user=self.business_user, type=Profile.BUSINESS)
        Profile.objects.create(user=self.customer_user, type=Profile.CUSTOMER)

    def test_business_user_can_create_offer(self):
        response = self._post_as_business()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_response_status_is_created(self):
        response = self._post_as_business()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_response_field_set_is_exact(self):
        response = self._post_as_business()
        self.assertEqual(set(response.data.keys()), {
            'id',
            'title',
            'image',
            'description',
            'details',
        })

    def test_response_detail_field_set_is_exact(self):
        response = self._post_as_business()
        self.assertEqual(set(response.data['details'][0].keys()), {
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        })

    def test_created_offer_user_is_request_user(self):
        self._post_as_business()
        self.assertEqual(Offer.objects.get().user, self.business_user)

    def test_exactly_three_offer_details_are_created(self):
        self._post_as_business()
        self.assertEqual(OfferDetail.objects.count(), 3)

    def test_basic_standard_premium_details_are_created(self):
        self._post_as_business()
        offer_types = set(OfferDetail.objects.values_list('offer_type', flat=True))
        self.assertEqual(offer_types, {
            OfferDetail.BASIC,
            OfferDetail.STANDARD,
            OfferDetail.PREMIUM,
        })

    def test_customer_user_gets_forbidden(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_without_profile_gets_forbidden(self):
        user = User.objects.create_user(username='noProfile')
        self.client.force_authenticate(user=user)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_gets_unauthorized(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_fewer_than_three_details_returns_bad_request(self):
        payload = self._payload(details=self._details()[:2])
        response = self._post_as_business(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_offer_type_returns_bad_request(self):
        details = self._details()
        details[1]['offer_type'] = OfferDetail.BASIC
        response = self._post_as_business(self._payload(details))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_package_type_returns_bad_request(self):
        details = self._details()
        details[2]['offer_type'] = OfferDetail.STANDARD
        response = self._post_as_business(self._payload(details))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_nested_detail_returns_bad_request(self):
        details = self._details()
        details[0]['delivery_time_in_days'] = 0
        response = self._post_as_business(self._payload(details))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_choose_another_offer_user(self):
        payload = self._payload()
        payload['user'] = self.customer_user.id
        self._post_as_business(payload)
        self.assertEqual(Offer.objects.get().user, self.business_user)

    def test_failed_validation_creates_no_partial_data(self):
        payload = self._payload(details=self._details()[:2])
        self._post_as_business(payload)
        self.assertEqual(Offer.objects.count(), 0)
        self.assertEqual(OfferDetail.objects.count(), 0)

    def _post_as_business(self, payload=None):
        self.client.force_authenticate(user=self.business_user)
        return self.client.post(self.url, payload or self._payload(), format='json')

    def _payload(self, details=None):
        return {
            'title': 'Grafikdesign-Paket',
            'image': None,
            'description': 'Ein umfassendes Grafikdesign-Paket.',
            'details': details or self._details(),
        }

    def _details(self):
        return [
            self._detail('Basic Design', OfferDetail.BASIC, 100),
            self._detail('Standard Design', OfferDetail.STANDARD, 200),
            self._detail('Premium Design', OfferDetail.PREMIUM, 500),
        ]

    def _detail(self, title, offer_type, price):
        return {
            'title': title,
            'revisions': 2,
            'delivery_time_in_days': 5,
            'price': price,
            'features': ['Logo Design', 'Visitenkarte'],
            'offer_type': offer_type,
        }


class OfferListViewTests(APITestCase):
    """Tests for the public offer list endpoint."""

    def setUp(self):
        self.url = reverse('offers_app:offer-create')
        self.user = User.objects.create_user(
            username='businessUser',
            first_name='Business',
            last_name='User',
        )
        Profile.objects.create(user=self.user, type=Profile.BUSINESS)

    def test_public_get_returns_ok(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_get_works(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_paginated_response_has_exact_top_level_fields(self):
        response = self.client.get(self.url)
        self.assertEqual(set(response.data.keys()), {
            'count',
            'next',
            'previous',
            'results',
        })

    def test_result_field_set_is_exact(self):
        self._create_offer('Logo', 'Logo design')
        response = self.client.get(self.url)
        self.assertEqual(set(response.data['results'][0].keys()), {
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
        })

    def test_detail_link_shape_is_exact(self):
        self._create_offer('Logo', 'Logo design')
        response = self.client.get(self.url)
        detail = response.data['results'][0]['details'][0]
        self.assertEqual(set(detail.keys()), {'id', 'url'})
        self.assertIn(f'/api/offerdetails/{detail["id"]}/', detail['url'])

    def test_user_details_shape_is_exact(self):
        self._create_offer('Logo', 'Logo design')
        response = self.client.get(self.url)
        user_details = response.data['results'][0]['user_details']
        self.assertEqual(set(user_details.keys()), {
            'first_name',
            'last_name',
            'username',
        })

    def test_creator_id_returns_only_creators_offers(self):
        own_offer = self._create_offer('Own', 'Own description')
        other_user = User.objects.create_user(username='other')
        self._create_offer('Other', 'Other description', user=other_user)
        response = self.client.get(self.url, {'creator_id': self.user.id})
        ids = [offer['id'] for offer in response.data['results']]
        self.assertEqual(ids, [own_offer.id])

    def test_creator_id_excludes_another_creator(self):
        other_user = User.objects.create_user(username='other')
        other_offer = self._create_offer('Other', 'Other', user=other_user)
        self._create_offer('Own', 'Own', user=self.user)
        response = self.client.get(self.url, {'creator_id': self.user.id})
        ids = [offer['id'] for offer in response.data['results']]
        self.assertNotIn(other_offer.id, ids)

    def test_invalid_creator_id_returns_bad_request(self):
        response = self.client.get(self.url, {'creator_id': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_min_price_filters_using_minimum_detail_price(self):
        self._create_offer('Cheap', 'Cheap', prices=[80, 150, 300])
        included = self._create_offer('Costly', 'Costly', prices=[120, 150, 300])
        response = self.client.get(self.url, {'min_price': '100'})
        ids = [offer['id'] for offer in response.data['results']]
        self.assertEqual(ids, [included.id])

    def test_min_price_exact_boundary_works(self):
        offer = self._create_offer('Boundary', 'Boundary', prices=[100, 200, 300])
        response = self.client.get(self.url, {'min_price': '100'})
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(offer.id, ids)

    def test_invalid_min_price_returns_bad_request(self):
        response = self.client.get(self.url, {'min_price': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_max_delivery_time_filters_shortest_delivery_time(self):
        included = self._create_offer('Fast', 'Fast', delivery_times=[5, 7, 10])
        self._create_offer('Slow', 'Slow', delivery_times=[6, 8, 10])
        response = self.client.get(self.url, {'max_delivery_time': '5'})
        ids = [offer['id'] for offer in response.data['results']]
        self.assertEqual(ids, [included.id])

    def test_max_delivery_time_exact_boundary_works(self):
        offer = self._create_offer('Boundary', 'Boundary', delivery_times=[5, 9, 11])
        response = self.client.get(self.url, {'max_delivery_time': '5'})
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(offer.id, ids)

    def test_invalid_max_delivery_time_returns_bad_request(self):
        response = self.client.get(self.url, {'max_delivery_time': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_by_title(self):
        offer = self._create_offer('Brand Kit', 'Design package')
        self._create_offer('Website', 'Development package')
        response = self.client.get(self.url, {'search': 'Brand'})
        self.assertEqual(response.data['results'][0]['id'], offer.id)

    def test_search_by_description(self):
        offer = self._create_offer('Logo', 'Includes stationery')
        self._create_offer('Website', 'Landing page')
        response = self.client.get(self.url, {'search': 'stationery'})
        self.assertEqual(response.data['results'][0]['id'], offer.id)

    def test_search_is_case_insensitive(self):
        offer = self._create_offer('Premium Logo', 'Design package')
        response = self.client.get(self.url, {'search': 'premium'})
        self.assertEqual(response.data['results'][0]['id'], offer.id)

    def test_search_excludes_unrelated_offers(self):
        self._create_offer('Logo', 'Branding')
        self._create_offer('Website', 'Development')
        response = self.client.get(self.url, {'search': 'branding'})
        self.assertEqual(response.data['count'], 1)

    def test_ordering_updated_at_ascending(self):
        old_offer = self._create_offer('Old', 'Old')
        new_offer = self._create_offer('New', 'New')
        self._set_updated_at(old_offer, timezone.now() - timedelta(days=1))
        self._set_updated_at(new_offer, timezone.now())
        response = self.client.get(self.url, {'ordering': 'updated_at'})
        self.assertEqual(self._result_ids(response), [old_offer.id, new_offer.id])

    def test_ordering_updated_at_descending(self):
        old_offer = self._create_offer('Old', 'Old')
        new_offer = self._create_offer('New', 'New')
        self._set_updated_at(old_offer, timezone.now() - timedelta(days=1))
        self._set_updated_at(new_offer, timezone.now())
        response = self.client.get(self.url, {'ordering': '-updated_at'})
        self.assertEqual(self._result_ids(response), [new_offer.id, old_offer.id])

    def test_ordering_min_price_ascending(self):
        high = self._create_offer('High', 'High', prices=[200, 300, 400])
        low = self._create_offer('Low', 'Low', prices=[100, 300, 400])
        response = self.client.get(self.url, {'ordering': 'min_price'})
        self.assertEqual(self._result_ids(response), [low.id, high.id])

    def test_ordering_min_price_descending(self):
        high = self._create_offer('High', 'High', prices=[200, 300, 400])
        low = self._create_offer('Low', 'Low', prices=[100, 300, 400])
        response = self.client.get(self.url, {'ordering': '-min_price'})
        self.assertEqual(self._result_ids(response), [high.id, low.id])

    def test_invalid_ordering_returns_bad_request(self):
        response = self.client.get(self.url, {'ordering': 'title'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_custom_page_size_works(self):
        self._create_offers(3)
        response = self.client.get(self.url, {'page_size': '2'})
        self.assertEqual(len(response.data['results']), 2)

    def test_page_count_and_result_count_behave_correctly(self):
        self._create_offers(3)
        response = self.client.get(self.url, {'page_size': '2'})
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 2)

    def test_invalid_page_size_returns_bad_request(self):
        response = self.client.get(self.url, {'page_size': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_positive_page_size_returns_bad_request(self):
        response = self.client.get(self.url, {'page_size': '0'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_remains_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_still_requires_authentication(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_post_still_returns_forbidden(self):
        customer = User.objects.create_user(username='customer')
        Profile.objects.create(user=customer, type=Profile.CUSTOMER)
        self.client.force_authenticate(user=customer)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_business_post_still_returns_created(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def _create_offers(self, amount):
        for index in range(amount):
            self._create_offer(f'Offer {index}', f'Description {index}')

    def _create_offer(
        self,
        title,
        description,
        user=None,
        prices=None,
        delivery_times=None,
    ):
        offer = Offer.objects.create(
            user=user or self.user,
            title=title,
            description=description,
        )
        self._create_details(offer, prices, delivery_times)
        return offer

    def _create_details(self, offer, prices=None, delivery_times=None):
        prices = prices or [100, 200, 300]
        delivery_times = delivery_times or [5, 7, 10]
        offer_types = [OfferDetail.BASIC, OfferDetail.STANDARD, OfferDetail.PREMIUM]
        for index, offer_type in enumerate(offer_types):
            self._create_detail(offer, offer_type, prices[index], delivery_times[index])

    def _create_detail(self, offer, offer_type, price, delivery_time):
        return OfferDetail.objects.create(
            offer=offer,
            title=f'{offer_type.title()} Package',
            revisions=2,
            delivery_time_in_days=delivery_time,
            price=Decimal(price),
            features=['Feature'],
            offer_type=offer_type,
        )

    def _set_updated_at(self, offer, value):
        Offer.objects.filter(pk=offer.pk).update(updated_at=value)

    def _result_ids(self, response):
        return [offer['id'] for offer in response.data['results']]

    def _payload(self):
        return {
            'title': 'Grafikdesign-Paket',
            'image': None,
            'description': 'Ein umfassendes Grafikdesign-Paket.',
            'details': [
                self._payload_detail(OfferDetail.BASIC),
                self._payload_detail(OfferDetail.STANDARD),
                self._payload_detail(OfferDetail.PREMIUM),
            ],
        }

    def _payload_detail(self, offer_type):
        return {
            'title': f'{offer_type.title()} Design',
            'revisions': 2,
            'delivery_time_in_days': 5,
            'price': 100,
            'features': ['Logo Design'],
            'offer_type': offer_type,
        }


class OfferRetrieveViewTests(APITestCase):
    """Tests for the authenticated offer retrieve endpoint."""

    def setUp(self):
        self.creator = User.objects.create_user(username='creator')
        self.business_user = User.objects.create_user(username='business')
        self.customer_user = User.objects.create_user(username='customer')
        Profile.objects.create(user=self.creator, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_user, type=Profile.BUSINESS)
        Profile.objects.create(user=self.customer_user, type=Profile.CUSTOMER)
        self.offer = self._create_offer()
        self.url = reverse('offers_app:offer-detail', kwargs={'pk': self.offer.id})

    def test_authenticated_user_can_retrieve_offer(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_business_user_can_retrieve_offer(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_user_can_retrieve_offer(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_status_is_ok(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_field_set_is_exact(self):
        response = self._get_as_business()
        self.assertEqual(set(response.data.keys()), {
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
        })

    def test_user_contains_creator_user_id(self):
        response = self._get_as_business()
        self.assertEqual(response.data['user'], self.creator.id)

    def test_user_details_is_not_present(self):
        response = self._get_as_business()
        self.assertNotIn('user_details', response.data)

    def test_detail_objects_contain_exactly_id_and_url(self):
        response = self._get_as_business()
        detail = response.data['details'][0]
        self.assertEqual(set(detail.keys()), {'id', 'url'})

    def test_detail_urls_point_to_offer_detail_endpoint(self):
        response = self._get_as_business()
        detail = response.data['details'][0]
        self.assertIn(f'/api/offerdetails/{detail["id"]}/', detail['url'])

    def test_min_price_is_correct(self):
        response = self._get_as_business()
        self.assertEqual(response.data['min_price'], Decimal('100.00'))

    def test_min_delivery_time_is_correct(self):
        response = self._get_as_business()
        self.assertEqual(response.data['min_delivery_time'], 5)

    def test_unauthenticated_request_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_offer_id_returns_not_found(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get(
            reverse('offers_app:offer-detail', kwargs={'pk': 999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_existing_list_endpoint_still_works(self):
        response = self.client.get(reverse('offers_app:offer-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_existing_create_endpoint_still_works(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.post(
            reverse('offers_app:offer-create'),
            self._payload(),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def _get_as_business(self):
        self.client.force_authenticate(user=self.business_user)
        return self.client.get(self.url)

    def _create_offer(self):
        offer = Offer.objects.create(
            user=self.creator,
            title='Logo Design',
            description='Professional logo design package',
        )
        self._create_detail(offer, OfferDetail.BASIC, 100, 5)
        self._create_detail(offer, OfferDetail.STANDARD, 200, 7)
        self._create_detail(offer, OfferDetail.PREMIUM, 500, 10)
        return offer

    def _create_detail(self, offer, offer_type, price, delivery_time):
        return OfferDetail.objects.create(
            offer=offer,
            title=f'{offer_type.title()} Package',
            revisions=2,
            delivery_time_in_days=delivery_time,
            price=Decimal(price),
            features=['Feature'],
            offer_type=offer_type,
        )

    def _payload(self):
        return {
            'title': 'Grafikdesign-Paket',
            'image': None,
            'description': 'Ein umfassendes Grafikdesign-Paket.',
            'details': [
                self._payload_detail(OfferDetail.BASIC),
                self._payload_detail(OfferDetail.STANDARD),
                self._payload_detail(OfferDetail.PREMIUM),
            ],
        }

    def _payload_detail(self, offer_type):
        return {
            'title': f'{offer_type.title()} Design',
            'revisions': 2,
            'delivery_time_in_days': 5,
            'price': 100,
            'features': ['Logo Design'],
            'offer_type': offer_type,
        }


class OfferPatchViewTests(APITestCase):
    """Tests for the authenticated owner-only offer PATCH endpoint."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner')
        self.other_user = User.objects.create_user(username='other')
        Profile.objects.create(user=self.owner, type=Profile.BUSINESS)
        Profile.objects.create(user=self.other_user, type=Profile.BUSINESS)
        self.offer = Offer.objects.create(
            user=self.owner,
            title='Logo Design',
            description='Original description',
        )
        self.basic = self._create_detail(OfferDetail.BASIC, 'Basic', 100)
        self.standard = self._create_detail(OfferDetail.STANDARD, 'Standard', 200)
        self.premium = self._create_detail(OfferDetail.PREMIUM, 'Premium', 500)
        self.url = reverse('offers_app:offer-detail', kwargs={'pk': self.offer.id})

    def test_owner_can_patch(self):
        response = self._patch_as_owner({'title': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_owner_gets_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(self.url, {'title': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gets_unauthorized(self):
        response = self.client.patch(self.url, {'title': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_title_can_be_updated(self):
        self._patch_as_owner({'title': 'Updated title'})
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.title, 'Updated title')

    def test_description_can_be_updated(self):
        self._patch_as_owner({'description': 'Updated description'})
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.description, 'Updated description')

    def test_partial_patch_leaves_omitted_fields_unchanged(self):
        self._patch_as_owner({'title': 'Updated title'})
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.description, 'Original description')

    def test_offer_user_remains_unchanged(self):
        self._patch_as_owner({'user': self.other_user.id})
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.user, self.owner)

    def test_one_detail_can_be_updated(self):
        self._patch_as_owner({'details': [self._detail_payload('Updated Basic')]})
        self.basic.refresh_from_db()
        self.assertEqual(self.basic.title, 'Updated Basic')

    def test_updated_detail_keeps_same_id(self):
        original_id = self.basic.id
        self._patch_as_owner({'details': [self._detail_payload('Updated Basic')]})
        self.basic.refresh_from_db()
        self.assertEqual(self.basic.id, original_id)

    def test_other_two_details_keep_their_ids(self):
        standard_id = self.standard.id
        premium_id = self.premium.id
        self._patch_as_owner({'details': [self._detail_payload('Updated Basic')]})
        self.standard.refresh_from_db()
        self.premium.refresh_from_db()
        self.assertEqual(self.standard.id, standard_id)
        self.assertEqual(self.premium.id, premium_id)

    def test_other_two_details_remain_unchanged(self):
        self._patch_as_owner({'details': [self._detail_payload('Updated Basic')]})
        self.standard.refresh_from_db()
        self.premium.refresh_from_db()
        self.assertEqual(self.standard.title, 'Standard')
        self.assertEqual(self.premium.title, 'Premium')

    def test_response_contains_all_three_details(self):
        response = self._patch_as_owner({'details': [self._detail_payload()]})
        self.assertEqual(len(response.data['details']), 3)

    def test_invalid_offer_type_returns_bad_request(self):
        payload = self._detail_payload(offer_type='gold')
        response = self._patch_as_owner({'details': [payload]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_fourth_detail_cannot_be_created(self):
        self.premium.delete()
        response = self._patch_as_owner({
            'details': [self._detail_payload(offer_type=OfferDetail.PREMIUM)],
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.offer.details.filter(
            offer_type=OfferDetail.PREMIUM,
        ).exists())

    def test_invalid_nested_data_returns_bad_request(self):
        payload = self._detail_payload(delivery_time_in_days=0)
        response = self._patch_as_owner({'details': [payload]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_nested_update_does_not_modify_offer(self):
        response = self._patch_as_owner({
            'title': 'Changed',
            'details': [self._detail_payload(delivery_time_in_days=0)],
        })
        self.offer.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.offer.title, 'Logo Design')

    def test_nonexistent_offer_returns_not_found(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            reverse('offers_app:offer-detail', kwargs={'pk': 999}),
            {'title': 'Updated'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_still_get(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_owner_authenticated_user_can_still_get(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_get_still_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_response_field_set_is_exact(self):
        response = self._patch_as_owner({'title': 'Updated'})
        self.assertEqual(set(response.data.keys()), {
            'id',
            'title',
            'image',
            'description',
            'details',
        })

    def test_response_detail_field_set_is_exact(self):
        response = self._patch_as_owner({'title': 'Updated'})
        self.assertEqual(set(response.data['details'][0].keys()), {
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        })

    def test_detail_id_cannot_be_changed(self):
        original_id = self.basic.id
        payload = self._detail_payload()
        payload['id'] = self.standard.id
        self._patch_as_owner({'details': [payload]})
        self.basic.refresh_from_db()
        self.assertEqual(self.basic.id, original_id)

    def _patch_as_owner(self, payload):
        self.client.force_authenticate(user=self.owner)
        return self.client.patch(self.url, payload, format='json')

    def _detail_payload(
        self,
        title='Basic Updated',
        offer_type=OfferDetail.BASIC,
        delivery_time_in_days=6,
    ):
        return {
            'title': title,
            'revisions': 3,
            'delivery_time_in_days': delivery_time_in_days,
            'price': 120,
            'features': ['Logo Design', 'Flyer'],
            'offer_type': offer_type,
        }

    def _create_detail(self, offer_type, title, price):
        return OfferDetail.objects.create(
            offer=self.offer,
            title=title,
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal(price),
            features=['Feature'],
            offer_type=offer_type,
        )


class OfferDeleteViewTests(APITestCase):
    """Tests for the authenticated owner-only offer DELETE endpoint."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner')
        self.other_user = User.objects.create_user(username='other')
        Profile.objects.create(user=self.owner, type=Profile.BUSINESS)
        Profile.objects.create(user=self.other_user, type=Profile.BUSINESS)
        self.offer = Offer.objects.create(
            user=self.owner,
            title='Logo Design',
            description='Original description',
        )
        self._create_detail(OfferDetail.BASIC)
        self._create_detail(OfferDetail.STANDARD)
        self._create_detail(OfferDetail.PREMIUM)
        self.url = reverse('offers_app:offer-detail', kwargs={'pk': self.offer.id})

    def test_owner_can_delete_own_offer(self):
        response = self._delete_as_owner()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_successful_delete_returns_no_content(self):
        response = self._delete_as_owner()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_response_body_is_empty(self):
        response = self._delete_as_owner()
        self.assertIsNone(response.data)

    def test_offer_no_longer_exists_after_delete(self):
        self._delete_as_owner()
        self.assertFalse(Offer.objects.filter(pk=self.offer.pk).exists())

    def test_related_offer_details_are_deleted(self):
        self._delete_as_owner()
        self.assertEqual(OfferDetail.objects.count(), 0)

    def test_non_owner_gets_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_gets_unauthorized(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_offer_returns_not_found(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            reverse('offers_app:offer-detail', kwargs={'pk': 999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_still_works_for_authenticated_non_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_still_remains_owner_only(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            self.url,
            {'title': 'Updated'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_existing_list_behavior_remains_unchanged(self):
        response = self.client.get(reverse('offers_app:offer-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_existing_create_behavior_remains_unchanged(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse('offers_app:offer-create'),
            self._payload(),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def _delete_as_owner(self):
        self.client.force_authenticate(user=self.owner)
        return self.client.delete(self.url)

    def _create_detail(self, offer_type):
        return OfferDetail.objects.create(
            offer=self.offer,
            title=f'{offer_type.title()} Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('100.00'),
            features=['Feature'],
            offer_type=offer_type,
        )

    def _payload(self):
        return {
            'title': 'Grafikdesign-Paket',
            'image': None,
            'description': 'Ein umfassendes Grafikdesign-Paket.',
            'details': [
                self._payload_detail(OfferDetail.BASIC),
                self._payload_detail(OfferDetail.STANDARD),
                self._payload_detail(OfferDetail.PREMIUM),
            ],
        }

    def _payload_detail(self, offer_type):
        return {
            'title': f'{offer_type.title()} Design',
            'revisions': 2,
            'delivery_time_in_days': 5,
            'price': 100,
            'features': ['Logo Design'],
            'offer_type': offer_type,
        }


class OfferDetailRetrieveViewTests(APITestCase):
    """Tests for the authenticated offer detail retrieve endpoint."""

    def setUp(self):
        self.creator = User.objects.create_user(username='creator')
        self.business_user = User.objects.create_user(username='business')
        self.customer_user = User.objects.create_user(username='customer')
        Profile.objects.create(user=self.creator, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_user, type=Profile.BUSINESS)
        Profile.objects.create(user=self.customer_user, type=Profile.CUSTOMER)
        self.offer = Offer.objects.create(
            user=self.creator,
            title='Logo Design',
            description='Professional logo design package',
        )
        self.detail = self._create_detail(OfferDetail.BASIC)
        self.url = reverse(
            'offers_app:offer-detail-detail',
            kwargs={'pk': self.detail.id},
        )

    def test_business_user_can_retrieve_offer_detail(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_user_can_retrieve_offer_detail(self):
        response = self._get_as(self.customer_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_request_returns_ok(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_field_set_is_exact(self):
        response = self._get_as(self.business_user)
        self.assertEqual(set(response.data.keys()), {
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        })

    def test_id_is_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.data['id'], self.detail.id)

    def test_title_is_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.data['title'], self.detail.title)

    def test_revisions_is_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.data['revisions'], self.detail.revisions)

    def test_delivery_time_in_days_is_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(
            response.data['delivery_time_in_days'],
            self.detail.delivery_time_in_days,
        )

    def test_price_is_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.data['price'], '100.00')

    def test_features_are_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.data['features'], ['Logo Design'])

    def test_offer_type_is_correct(self):
        response = self._get_as(self.business_user)
        self.assertEqual(response.data['offer_type'], OfferDetail.BASIC)

    def test_response_does_not_contain_offer(self):
        response = self._get_as(self.business_user)
        self.assertNotIn('offer', response.data)

    def test_unauthenticated_request_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_offer_detail_returns_not_found(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get(
            reverse('offers_app:offer-detail-detail', kwargs={'pk': 999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_detail_url_resolves_to_offer_detail_endpoint(self):
        response = self.client.get(reverse('offers_app:offer-create'))
        detail_url = response.data['results'][0]['details'][0]['url']
        self.assertEqual(detail_url, self._absolute_detail_url())

    def test_offer_detail_url_resolves_to_offer_detail_endpoint(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get(
            reverse('offers_app:offer-detail', kwargs={'pk': self.offer.id}),
        )
        detail_url = response.data['details'][0]['url']
        self.assertEqual(detail_url, self._absolute_detail_url())

    def _get_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.get(self.url)

    def _create_detail(self, offer_type):
        return OfferDetail.objects.create(
            offer=self.offer,
            title='Basic Package',
            revisions=2,
            delivery_time_in_days=5,
            price=Decimal('100.00'),
            features=['Logo Design'],
            offer_type=offer_type,
        )

    def _absolute_detail_url(self):
        path = reverse(
            'offers_app:offer-detail-detail',
            kwargs={'pk': self.detail.id},
        )
        return f'http://testserver{path}'
