"""URL routes for profile API endpoints."""

from django.urls import path

from profile_app.api.views import (
    BusinessProfileListView,
    CustomerProfileListView,
    ProfileDetailView,
)


app_name = 'profile_app'

urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),
    path(
        'profiles/business/',
        BusinessProfileListView.as_view(),
        name='business-profile-list',
    ),
    path(
        'profiles/customer/',
        CustomerProfileListView.as_view(),
        name='customer-profile-list',
    ),
]
