"""URL routes for core API endpoints."""

from django.urls import path

from core.api.views import BaseInfoView


app_name = 'core_api'

urlpatterns = [
    path('base-info/', BaseInfoView.as_view(), name='base-info'),
]
