"""URL routes for review API endpoints."""

from django.urls import path

from reviews_app.api.views import ReviewListCreateView


app_name = 'reviews_app'

urlpatterns = [
    path('reviews/', ReviewListCreateView.as_view(), name='review-list'),
]
