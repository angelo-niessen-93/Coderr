from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from offers_app.models import Offer, OfferDetail
from profile_app.models import Profile
from reviews_app.models import Review


User = get_user_model()


class BaseInfoViewTests(APITestCase):
    """Tests for the public base-info aggregate endpoint."""

    def setUp(self):
        self.url = reverse('core_api:base-info')

    def test_unauthenticated_request_returns_ok(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_request_returns_ok(self):
        user = User.objects.create_user(username='authUser')
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_field_set_is_exact(self):
        response = self.client.get(self.url)
        self.assertEqual(set(response.data.keys()), self._base_info_fields())

    def test_counts_all_reviews_correctly(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data['review_count'], 3)

    def test_zero_reviews_returns_zero_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data['review_count'], 0)

    def test_average_rating_is_correct(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data['average_rating'], 4.7)

    def test_average_rating_is_rounded_to_one_decimal(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data['average_rating'], round(14 / 3, 1))

    def test_average_rating_is_numeric(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertIsInstance(response.data['average_rating'], float)

    def test_no_reviews_returns_zero_average(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data['average_rating'], 0.0)

    def test_counts_business_profiles(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data['business_profile_count'], 2)

    def test_excludes_customer_profiles_from_business_count(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertNotEqual(response.data['business_profile_count'], 3)

    def test_excludes_users_without_profile_from_business_count(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data['business_profile_count'], 2)

    def test_counts_all_offers(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data['offer_count'], 2)

    def test_offer_details_are_not_counted_as_offers(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertNotEqual(response.data['offer_count'], 5)

    def test_mixed_dataset_returns_all_values(self):
        self._create_dataset()
        response = self.client.get(self.url)
        self.assertEqual(response.data, {
            'review_count': 3,
            'average_rating': 4.7,
            'business_profile_count': 2,
            'offer_count': 2,
        })

    def test_review_routes_still_resolve(self):
        self.assertEqual(reverse('reviews_app:review-list'), '/api/reviews/')
        self.assertEqual(
            reverse('reviews_app:review-detail', kwargs={'pk': 1}),
            '/api/reviews/1/',
        )

    def test_order_routes_still_resolve(self):
        self.assertEqual(reverse('orders_app:order-create'), '/api/orders/')
        self.assertEqual(
            reverse('orders_app:order-detail', kwargs={'pk': 1}),
            '/api/orders/1/',
        )

    def test_order_count_routes_still_resolve(self):
        self.assertEqual(
            reverse('orders_app:order-count', kwargs={'business_user_id': 1}),
            '/api/order-count/1/',
        )
        self.assertEqual(
            reverse(
                'orders_app:completed-order-count',
                kwargs={'business_user_id': 1},
            ),
            '/api/completed-order-count/1/',
        )

    def test_auth_profile_and_offer_routes_still_resolve(self):
        self.assertEqual(reverse('auth_app:login'), '/api/login/')
        self.assertEqual(reverse('auth_app:registration'), '/api/registration/')
        self.assertEqual(
            reverse('profile_app:profile-detail', kwargs={'pk': 1}),
            '/api/profile/1/',
        )
        self.assertEqual(reverse('offers_app:offer-create'), '/api/offers/')

    def _create_dataset(self):
        customer, customer_two = self._create_customers()
        business, business_two = self._create_business_users()
        User.objects.create_user(username='noProfile')
        self._create_reviews(customer, customer_two, business, business_two)
        self._create_offers(business, business_two)

    def _create_customers(self):
        customer = User.objects.create_user(username='customer')
        customer_two = User.objects.create_user(username='customerTwo')
        Profile.objects.create(user=customer, type=Profile.CUSTOMER)
        return customer, customer_two

    def _create_business_users(self):
        business = User.objects.create_user(username='business')
        business_two = User.objects.create_user(username='businessTwo')
        Profile.objects.create(user=business, type=Profile.BUSINESS)
        Profile.objects.create(user=business_two, type=Profile.BUSINESS)
        return business, business_two

    def _create_reviews(self, customer, customer_two, business, business_two):
        review_data = [
            (business, customer, 4, 'Good work.'),
            (business, customer_two, 5, 'Great work.'),
            (business_two, customer, 5, 'Great again.'),
        ]
        for business_user, reviewer, rating, description in review_data:
            self._create_review(business_user, reviewer, rating, description)

    def _create_review(self, business_user, reviewer, rating, description):
        return Review.objects.create(
            business_user=business_user,
            reviewer=reviewer,
            rating=rating,
            description=description,
        )

    def _create_offers(self, business, business_two):
        offer = self._create_offer(business, 'Logo Offer')
        offer_two = self._create_offer(business_two, 'Design Offer')
        self._create_detail(offer, OfferDetail.BASIC)
        self._create_detail(offer, OfferDetail.STANDARD)
        self._create_detail(offer_two, OfferDetail.PREMIUM)

    def _create_offer(self, user, title):
        return Offer.objects.create(
            user=user,
            title=title,
            description='Offer description.',
        )

    def _create_detail(self, offer, offer_type):
        return OfferDetail.objects.create(
            offer=offer,
            title='Package',
            revisions=2,
            delivery_time_in_days=5,
            price='99.99',
            features=['Feature'],
            offer_type=offer_type,
        )

    def _base_info_fields(self):
        return {
            'review_count',
            'average_rating',
            'business_profile_count',
            'offer_count',
        }

