from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

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

