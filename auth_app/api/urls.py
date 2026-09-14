"""URL routes for authentication API endpoints."""

from django.urls import path

from auth_app.api.views import LoginView, RegistrationView


app_name = 'auth_app'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('registration/', RegistrationView.as_view(), name='registration'),
]
