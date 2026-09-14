"""URL routes for offer API endpoints."""

from django.urls import path

from offers_app.api.views import (
    OfferDetailRetrieveView,
    OfferListCreateView,
    OfferRetrieveView,
)


app_name = 'offers_app'

urlpatterns = [
    path('offers/', OfferListCreateView.as_view(), name='offer-create'),
    path('offers/<int:pk>/', OfferRetrieveView.as_view(), name='offer-detail'),
    path(
        'offerdetails/<int:pk>/',
        OfferDetailRetrieveView.as_view(),
        name='offer-detail-detail',
    ),
]
