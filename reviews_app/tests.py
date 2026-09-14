from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

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



