"""Views for authentication API endpoints."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

from auth_app.api.serializers import LoginSerializer, RegistrationSerializer


class RegistrationView(APIView):
    """Create a user account, profile, and authentication token."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        return Response(
            self._response_data(registration),
            status=status.HTTP_201_CREATED,
        )

    def _response_data(self, registration):
        user = registration['user']
        return {
            'token': registration['token'],
            'username': user.username,
            'email': user.email,
            'user_id': user.id,
        }


class LoginView(APIView):
    """Authenticate a user and return the DRF token."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response(self._response_data(user, token.key))

    def _response_data(self, user, token_key):
        return {
            'token': token_key,
            'username': user.username,
            'email': user.email,
            'user_id': user.id,
        }
