from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from profile_app.models import Profile
from reviews_app.api.serializers import (
    ReviewSerializer,
    ReviewUpdateSerializer,
)
from reviews_app.models import Review


User = get_user_model()


class ReviewModelTests(TestCase):
    """Tests for the Review data model."""

    def setUp(self):
        self.business = User.objects.create_user(username='business')
        self.business_two = User.objects.create_user(username='businessTwo')
        self.reviewer = User.objects.create_user(username='reviewer')
        self.reviewer_two = User.objects.create_user(username='reviewerTwo')
        self.review = self._create_review()

    def test_review_can_be_created(self):
        self.assertEqual(Review.objects.count(), 1)

    def test_business_user_relation_works(self):
        self.assertEqual(self.review.business_user, self.business)

    def test_reviewer_relation_works(self):
        self.assertEqual(self.review.reviewer, self.reviewer)

    def test_rating_is_stored_correctly(self):
        self.assertEqual(self.review.rating, 4)

    def test_description_is_stored_correctly(self):
        self.assertEqual(self.review.description, 'Great collaboration.')

    def test_created_at_is_populated(self):
        self.assertIsNotNone(self.review.created_at)

    def test_updated_at_is_populated(self):
        self.assertIsNotNone(self.review.updated_at)

    def test_str_returns_readable_value(self):
        self.assertEqual(str(self.review), 'Review 4/5 for business')

    def test_rating_one_is_valid(self):
        review = self._unsaved_review(rating=1)
        review.full_clean()

    def test_rating_five_is_valid(self):
        review = self._unsaved_review(rating=5)
        review.full_clean()

    def test_rating_below_one_is_invalid(self):
        review = self._unsaved_review(rating=0)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_above_five_is_invalid(self):
        review = self._unsaved_review(rating=6)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_business_received_reviews_are_accessible(self):
        self.assertIn(self.review, self.business.received_reviews.all())

    def test_reviewer_written_reviews_are_accessible(self):
        self.assertIn(self.review, self.reviewer.written_reviews.all())

    def test_reverse_relations_do_not_conflict(self):
        self._create_review(business_user=self.business_two)
        self._create_review(reviewer=self.reviewer_two)
        self.assertEqual(self.business.received_reviews.count(), 2)
        self.assertEqual(self.reviewer.written_reviews.count(), 2)

    def test_duplicate_reviewer_business_pair_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._create_review()

    def test_same_reviewer_may_review_different_business_users(self):
        self._create_review(business_user=self.business_two)
        self.assertEqual(self.reviewer.written_reviews.count(), 2)

    def test_different_reviewers_may_review_same_business_user(self):
        self._create_review(reviewer=self.reviewer_two)
        self.assertEqual(self.business.received_reviews.count(), 2)

    def _create_review(self, business_user=None, reviewer=None, rating=4):
        return Review.objects.create(
            business_user=business_user or self.business,
            reviewer=reviewer or self.reviewer,
            rating=rating,
            description='Great collaboration.',
        )

    def _unsaved_review(self, rating):
        return Review(
            business_user=self.business_two,
            reviewer=self.reviewer_two,
            rating=rating,
            description='Useful feedback.',
        )

class ReviewSerializerTests(TestCase):
    """Tests for review serializers."""

    def setUp(self):
        self.business = User.objects.create_user(username='businessSer')
        self.business_two = User.objects.create_user(username='businessSerTwo')
        self.customer = User.objects.create_user(username='customerSer')
        self.no_profile_user = User.objects.create_user(username='noProfileSer')
        self.reviewer = User.objects.create_user(username='reviewerSer')
        self.reviewer_two = User.objects.create_user(username='reviewerSerTwo')
        Profile.objects.create(user=self.business, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_two, type=Profile.BUSINESS)
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        self.review = self._create_review()

    def test_review_serializer_field_set_is_exact(self):
        data = ReviewSerializer(self.review).data
        self.assertEqual(set(data.keys()), self._review_fields())

    def test_business_user_serialized_as_user_id(self):
        data = ReviewSerializer(self.review).data
        self.assertEqual(data['business_user'], self.business.id)

    def test_reviewer_serialized_as_user_id(self):
        data = ReviewSerializer(self.review).data
        self.assertEqual(data['reviewer'], self.reviewer.id)

    def test_rating_is_serialized_correctly(self):
        data = ReviewSerializer(self.review).data
        self.assertEqual(data['rating'], 4)

    def test_description_is_serialized_correctly(self):
        data = ReviewSerializer(self.review).data
        self.assertEqual(data['description'], 'Great collaboration.')

    def test_created_at_is_included(self):
        data = ReviewSerializer(self.review).data
        self.assertIn('created_at', data)

    def test_updated_at_is_included(self):
        data = ReviewSerializer(self.review).data
        self.assertIn('updated_at', data)

    def test_valid_business_user_is_accepted(self):
        serializer = self._create_serializer(reviewer=self.reviewer_two)
        self.assertTrue(serializer.is_valid())

    def test_customer_target_is_rejected(self):
        serializer = self._create_serializer(business_user=self.customer)
        self.assertFalse(serializer.is_valid())

    def test_user_without_profile_is_rejected(self):
        serializer = self._create_serializer(business_user=self.no_profile_user)
        self.assertFalse(serializer.is_valid())

    def test_rating_one_is_accepted(self):
        serializer = self._create_serializer(
            rating=1,
            reviewer=self.reviewer_two,
        )
        self.assertTrue(serializer.is_valid())

    def test_rating_five_is_accepted(self):
        serializer = self._create_serializer(
            rating=5,
            reviewer=self.reviewer_two,
        )
        self.assertTrue(serializer.is_valid())

    def test_rating_zero_is_rejected(self):
        serializer = self._create_serializer(
            rating=0,
            reviewer=self.reviewer_two,
        )
        self.assertFalse(serializer.is_valid())

    def test_rating_six_is_rejected(self):
        serializer = self._create_serializer(
            rating=6,
            reviewer=self.reviewer_two,
        )
        self.assertFalse(serializer.is_valid())

    def test_malformed_rating_is_rejected(self):
        serializer = self._create_serializer(
            rating='bad',
            reviewer=self.reviewer_two,
        )
        self.assertFalse(serializer.is_valid())

    def test_reviewer_is_not_client_writable(self):
        data = self._create_data(reviewer=self.reviewer_two.id)
        serializer = ReviewSerializer(
            data=data,
            context={'reviewer': self.reviewer_two},
        )
        self.assertFalse(serializer.is_valid())

    def test_create_can_save_reviewer_from_view(self):
        serializer = self._create_serializer(reviewer=self.reviewer_two)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(reviewer=self.reviewer_two)
        self.assertEqual(review.reviewer, self.reviewer_two)

    def test_duplicate_reviewer_business_user_is_rejected(self):
        serializer = self._create_serializer()
        self.assertFalse(serializer.is_valid())

    def test_same_reviewer_may_review_another_business_user(self):
        serializer = self._create_serializer(business_user=self.business_two)
        self.assertTrue(serializer.is_valid())

    def test_another_reviewer_may_review_same_business_user(self):
        serializer = self._create_serializer(reviewer=self.reviewer_two)
        self.assertTrue(serializer.is_valid())

    def test_update_rating_only_is_accepted(self):
        serializer = self._update_serializer({'rating': 5})
        self.assertTrue(serializer.is_valid())

    def test_update_description_only_is_accepted(self):
        serializer = self._update_serializer({'description': 'Updated text'})
        self.assertTrue(serializer.is_valid())

    def test_update_rating_and_description_is_accepted(self):
        serializer = self._update_serializer({
            'rating': 5,
            'description': 'Updated text',
        })
        self.assertTrue(serializer.is_valid())

    def test_update_invalid_rating_is_rejected(self):
        serializer = self._update_serializer({'rating': 6})
        self.assertFalse(serializer.is_valid())

    def test_update_business_user_is_rejected(self):
        serializer = self._update_serializer({
            'business_user': self.business_two.id,
        })
        self.assertFalse(serializer.is_valid())

    def test_update_reviewer_is_rejected(self):
        serializer = self._update_serializer({'reviewer': self.reviewer_two.id})
        self.assertFalse(serializer.is_valid())

    def test_update_id_is_rejected(self):
        serializer = self._update_serializer({'id': self.review.id})
        self.assertFalse(serializer.is_valid())

    def test_update_created_at_is_rejected(self):
        serializer = self._update_serializer({'created_at': self.review.created_at})
        self.assertFalse(serializer.is_valid())

    def test_update_forbidden_field_with_valid_field_is_rejected(self):
        serializer = self._update_serializer({
            'rating': 5,
            'business_user': self.business_two.id,
        })
        self.assertFalse(serializer.is_valid())

    def test_partial_update_keeps_omitted_fields_unchanged(self):
        serializer = self._update_serializer({'rating': 5})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        self.assertEqual(review.description, 'Great collaboration.')

    def test_partial_update_keeps_immutable_fields_unchanged(self):
        created_at = self.review.created_at
        serializer = self._update_serializer({'description': 'Updated text'})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        self.assertEqual(review.business_user, self.business)
        self.assertEqual(review.reviewer, self.reviewer)
        self.assertEqual(review.created_at, created_at)

    def _review_fields(self):
        return {
            'id',
            'business_user',
            'reviewer',
            'rating',
            'description',
            'created_at',
            'updated_at',
        }

    def _create_serializer(self, business_user=None, rating=4, reviewer=None):
        return ReviewSerializer(
            data=self._create_data(business_user, rating),
            context={'reviewer': reviewer or self.reviewer},
        )

    def _create_data(self, business_user=None, rating=4, reviewer=None):
        data = {
            'business_user': (business_user or self.business).id,
            'rating': rating,
            'description': 'Alles war toll!',
        }
        if reviewer is not None:
            data['reviewer'] = reviewer
        return data

    def _update_serializer(self, data):
        return ReviewUpdateSerializer(self.review, data=data, partial=True)

    def _create_review(self):
        return Review.objects.create(
            business_user=self.business,
            reviewer=self.reviewer,
            rating=4,
            description='Great collaboration.',
        )

class ReviewListCreateViewTests(APITestCase):
    """Tests for review list and create endpoints."""

    def setUp(self):
        self.customer = User.objects.create_user(username='apiCustomer')
        self.customer_two = User.objects.create_user(username='apiCustomerTwo')
        self.business = User.objects.create_user(username='apiBusiness')
        self.business_two = User.objects.create_user(username='apiBusinessTwo')
        self.business_three = User.objects.create_user(username='apiBusinessThree')
        self.no_profile_user = User.objects.create_user(username='apiNoProfile')
        self._create_profiles()
        self._create_reviews()
        self.url = reverse('reviews_app:review-list')

    def test_get_authenticated_customer_returns_ok(self):
        response = self._get_as(self.customer)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_authenticated_business_returns_ok(self):
        response = self._get_as(self.business)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_unauthenticated_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_response_is_plain_list(self):
        response = self._get_as(self.customer)
        self.assertIsInstance(response.data, list)

    def test_get_response_field_set_is_exact(self):
        response = self._get_as(self.customer)
        self.assertEqual(set(response.data[0].keys()), self._review_fields())

    def test_get_returns_all_reviews_without_filters(self):
        response = self._get_as(self.customer)
        self.assertEqual(len(response.data), 3)

    def test_business_user_filter_includes_matching_reviews(self):
        response = self._get_as(
            self.customer,
            f'{self.url}?business_user_id={self.business.id}',
        )
        self.assertEqual(self._ids(response), {self.review_a.id, self.review_c.id})

    def test_business_user_filter_excludes_other_businesses(self):
        response = self._get_as(
            self.customer,
            f'{self.url}?business_user_id={self.business.id}',
        )
        self.assertNotIn(self.review_b.id, self._ids(response))

    def test_reviewer_filter_includes_matching_reviews(self):
        response = self._get_as(
            self.customer,
            f'{self.url}?reviewer_id={self.customer.id}',
        )
        self.assertEqual(self._ids(response), {self.review_a.id, self.review_b.id})

    def test_reviewer_filter_excludes_other_reviewers(self):
        response = self._get_as(
            self.customer,
            f'{self.url}?reviewer_id={self.customer.id}',
        )
        self.assertNotIn(self.review_c.id, self._ids(response))

    def test_combined_filters_apply_together(self):
        response = self._get_as(
            self.customer,
            self._combined_filter_url(),
        )
        self.assertEqual(self._ids(response), {self.review_a.id})

    def test_ordering_updated_at_is_supported(self):
        response = self._get_as(self.customer, f'{self.url}?ordering=updated_at')
        self.assertEqual(self._ordered_ids(response), [
            self.review_a.id,
            self.review_b.id,
            self.review_c.id,
        ])

    def test_ordering_desc_updated_at_is_supported(self):
        response = self._get_as(self.customer, f'{self.url}?ordering=-updated_at')
        self.assertEqual(self._ordered_ids(response), [
            self.review_c.id,
            self.review_b.id,
            self.review_a.id,
        ])

    def test_ordering_rating_is_supported(self):
        response = self._get_as(self.customer, f'{self.url}?ordering=rating')
        self.assertEqual(self._ratings(response), [2, 3, 5])

    def test_ordering_desc_rating_is_supported(self):
        response = self._get_as(self.customer, f'{self.url}?ordering=-rating')
        self.assertEqual(self._ratings(response), [5, 3, 2])

    def test_invalid_ordering_does_not_crash(self):
        response = self._get_as(self.customer, f'{self.url}?ordering=reviewer')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_can_create_review(self):
        response = self._post_as(self.customer, self._valid_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_business_user_cannot_create_review(self):
        response = self._post_as(self.business, self._valid_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_without_profile_cannot_create_review(self):
        response = self._post_as(self.no_profile_user, self._valid_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_review(self):
        response = self.client.post(self.url, self._valid_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_created_reviewer_is_request_user(self):
        response = self._post_as(self.customer_two, self._valid_payload())
        review = Review.objects.get(id=response.data['id'])
        self.assertEqual(review.reviewer, self.customer_two)

    def test_created_business_user_is_stored(self):
        response = self._post_as(self.customer, self._valid_payload())
        self.assertEqual(response.data['business_user'], self.business_three.id)

    def test_created_rating_is_stored(self):
        response = self._post_as(self.customer, self._valid_payload(rating=5))
        self.assertEqual(response.data['rating'], 5)

    def test_created_description_is_stored(self):
        response = self._post_as(self.customer, self._valid_payload())
        self.assertEqual(response.data['description'], 'Alles war toll!')

    def test_post_response_field_set_is_exact(self):
        response = self._post_as(self.customer, self._valid_payload())
        self.assertEqual(set(response.data.keys()), self._review_fields())

    def test_customer_target_is_rejected(self):
        response = self._post_as(
            self.customer,
            self._valid_payload(business_user=self.customer.id),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_target_without_profile_is_rejected(self):
        response = self._post_as(
            self.customer,
            self._valid_payload(business_user=self.no_profile_user.id),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_business_user_is_rejected(self):
        response = self._post_as(
            self.customer,
            self._valid_payload(business_user=999),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_below_one_is_rejected(self):
        response = self._post_as(self.customer, self._valid_payload(rating=0))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_above_five_is_rejected(self):
        response = self._post_as(self.customer, self._valid_payload(rating=6))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_rating_is_rejected(self):
        response = self._post_as(self.customer, self._valid_payload(rating='bad'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_supplied_reviewer_is_rejected(self):
        payload = self._valid_payload(reviewer=self.customer_two.id)
        response = self._post_as(self.customer, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_review_is_rejected(self):
        payload = self._valid_payload(business_user=self.business.id)
        response = self._post_as(self.customer, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_customer_may_review_another_business(self):
        response = self._post_as(self.customer, self._valid_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_another_customer_may_review_same_business(self):
        payload = self._valid_payload(business_user=self.business_two.id)
        response = self._post_as(self.customer_two, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_auth_route_still_resolves(self):
        self.assertEqual(reverse('auth_app:login'), '/api/login/')

    def test_profile_route_still_resolves(self):
        url = reverse('profile_app:profile-detail', kwargs={'pk': self.customer.id})
        self.assertEqual(url, f'/api/profile/{self.customer.id}/')

    def test_offer_route_still_resolves(self):
        self.assertEqual(reverse('offers_app:offer-create'), '/api/offers/')

    def test_orders_route_still_resolves(self):
        self.assertEqual(reverse('orders_app:order-create'), '/api/orders/')

    def test_order_count_route_still_resolves(self):
        url = reverse(
            'orders_app:order-count',
            kwargs={'business_user_id': self.business.id},
        )
        self.assertEqual(url, f'/api/order-count/{self.business.id}/')

    def test_completed_order_count_route_still_resolves(self):
        url = reverse(
            'orders_app:completed-order-count',
            kwargs={'business_user_id': self.business.id},
        )
        self.assertEqual(
            url,
            f'/api/completed-order-count/{self.business.id}/',
        )

    def _create_profiles(self):
        Profile.objects.create(user=self.customer, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.customer_two, type=Profile.CUSTOMER)
        Profile.objects.create(user=self.business, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_two, type=Profile.BUSINESS)
        Profile.objects.create(user=self.business_three, type=Profile.BUSINESS)

    def _create_reviews(self):
        self.review_a = self._create_review(self.business, self.customer, 2)
        self.review_b = self._create_review(self.business_two, self.customer, 5)
        self.review_c = self._create_review(self.business, self.customer_two, 3)
        self._set_updated_at_values()

    def _set_updated_at_values(self):
        base_time = timezone.now()
        self._set_updated_at(self.review_a, base_time + timedelta(seconds=1))
        self._set_updated_at(self.review_b, base_time + timedelta(seconds=2))
        self._set_updated_at(self.review_c, base_time + timedelta(seconds=3))

    def _set_updated_at(self, review, value):
        Review.objects.filter(pk=review.pk).update(updated_at=value)
        review.updated_at = value

    def _create_review(self, business_user, reviewer, rating):
        return Review.objects.create(
            business_user=business_user,
            reviewer=reviewer,
            rating=rating,
            description='Existing review.',
        )

    def _valid_payload(self, business_user=None, rating=4, reviewer=None):
        payload = {
            'business_user': business_user or self.business_three.id,
            'rating': rating,
            'description': 'Alles war toll!',
        }
        if reviewer is not None:
            payload['reviewer'] = reviewer
        return payload

    def _get_as(self, user, url=None):
        self.client.force_authenticate(user=user)
        return self.client.get(url or self.url)

    def _post_as(self, user, payload):
        self.client.force_authenticate(user=user)
        return self.client.post(self.url, payload, format='json')

    def _combined_filter_url(self):
        return (
            f'{self.url}?business_user_id={self.business.id}'
            f'&reviewer_id={self.customer.id}'
        )

    def _review_fields(self):
        return {
            'id',
            'business_user',
            'reviewer',
            'rating',
            'description',
            'created_at',
            'updated_at',
        }

    def _ids(self, response):
        return {item['id'] for item in response.data}

    def _ordered_ids(self, response):
        return [item['id'] for item in response.data]

    def _ratings(self, response):
        return [item['rating'] for item in response.data]


