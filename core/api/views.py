"""Views for cross-app aggregate endpoints."""

from django.db.models import Avg
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from offers_app.models import Offer
from profile_app.models import Profile
from reviews_app.models import Review


class BaseInfoView(APIView):
    """Return public platform statistics."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'review_count': self._review_count(),
            'average_rating': self._average_rating(),
            'business_profile_count': self._business_profile_count(),
            'offer_count': self._offer_count(),
        })

    def _review_count(self):
        return Review.objects.count()

    def _average_rating(self):
        average = Review.objects.aggregate(average=Avg('rating'))['average']
        if average is None:
            return 0.0
        return round(average, 1)

    def _business_profile_count(self):
        return Profile.objects.filter(type=Profile.BUSINESS).count()

    def _offer_count(self):
        return Offer.objects.count()
