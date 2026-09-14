from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profile_app.models import Profile


User = get_user_model()


class RegistrationTests(APITestCase):
    """Tests for the Coderr registration endpoint."""

    def setUp(self):
        self.url = reverse('auth_app:registration')
        self.payload = {
            'username': 'exampleUsername',
            'email': 'example@mail.de',
            'password': 'examplePassword',
            'repeated_password': 'examplePassword',
            'type': Profile.CUSTOMER,
        }

    def test_successful_customer_registration(self):
        response = self.client.post(self.url, self.payload, format='json')
        profile = User.objects.get(username='exampleUsername').profile
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(profile.type, Profile.CUSTOMER)

    def test_successful_business_registration(self):
        self.payload['type'] = Profile.BUSINESS
        response = self.client.post(self.url, self.payload, format='json')
        profile = User.objects.get(username='exampleUsername').profile
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(profile.type, Profile.BUSINESS)

    def test_response_fields_are_exact(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(
            set(response.data.keys()),
            {'token', 'username', 'email', 'user_id'},
        )

    def test_profile_is_created_automatically(self):
        self.client.post(self.url, self.payload, format='json')
        user = User.objects.get(username='exampleUsername')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_password_mismatch_returns_bad_request(self):
        self.payload['repeated_password'] = 'differentPassword'
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_type_returns_bad_request(self):
        self.payload['type'] = 'freelancer'
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_username_returns_bad_request(self):
        self.payload.pop('username')
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_email_returns_bad_request(self):
        self.payload.pop('email')
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password_returns_bad_request(self):
        self.payload.pop('password')
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_username_returns_bad_request(self):
        User.objects.create_user(username='exampleUsername')
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_is_hashed(self):
        self.client.post(self.url, self.payload, format='json')
        user = User.objects.get(username='exampleUsername')
        self.assertNotEqual(user.password, 'examplePassword')
        self.assertTrue(user.check_password('examplePassword'))

    def test_token_is_created(self):
        response = self.client.post(self.url, self.payload, format='json')
        user = User.objects.get(username='exampleUsername')
        self.assertEqual(Token.objects.get(user=user).key, response.data['token'])


class LoginTests(APITestCase):
    """Tests for the Coderr login endpoint."""

    def setUp(self):
        self.url = reverse('auth_app:login')
        self.password = 'examplePassword'
        self.user = User.objects.create_user(
            username='exampleUsername',
            email='example@mail.de',
            password=self.password,
        )
        Profile.objects.create(user=self.user, type=Profile.CUSTOMER)
        self.payload = {
            'username': self.user.username,
            'password': self.password,
        }

    def test_successful_login_returns_status_ok(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_successful_login_returns_token(self):
        response = self.client.post(self.url, self.payload, format='json')
        token = Token.objects.get(user=self.user)
        self.assertEqual(response.data['token'], token.key)

    def test_response_fields_are_exact(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(
            set(response.data.keys()),
            {'token', 'username', 'email', 'user_id'},
        )

    def test_successful_login_returns_correct_user_data(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['user_id'], self.user.id)

    def test_existing_token_is_returned(self):
        token = Token.objects.create(user=self.user)
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.data['token'], token.key)

    def test_invalid_username_returns_bad_request(self):
        self.payload['username'] = 'unknownUsername'
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_password_returns_bad_request(self):
        self.payload['password'] = 'wrongPassword'
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_username_returns_bad_request(self):
        self.payload.pop('username')
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password_returns_bad_request(self):
        self.payload.pop('password')
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_does_not_create_another_user(self):
        user_count = User.objects.count()
        self.client.post(self.url, self.payload, format='json')
        self.assertEqual(User.objects.count(), user_count)

    def test_login_does_not_create_another_profile(self):
        profile_count = Profile.objects.count()
        self.client.post(self.url, self.payload, format='json')
        self.assertEqual(Profile.objects.count(), profile_count)
