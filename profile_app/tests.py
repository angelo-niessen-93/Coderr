from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from profile_app.api.serializers import (
    BusinessProfileListSerializer,
    CustomerProfileListSerializer,
    ProfileDetailSerializer,
)
from profile_app.models import Profile


User = get_user_model()


class ProfileSerializerTests(TestCase):
    """Tests for profile API serializers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='exampleUsername',
            email='example@mail.de',
            first_name='Example',
            last_name='User',
        )
        self.profile = Profile.objects.create(
            user=self.user,
            type=Profile.BUSINESS,
            location='Berlin',
            tel='123456',
            description='Profile description',
            working_hours='9-5',
        )

    def test_detail_serializer_fields_are_exact(self):
        serializer = ProfileDetailSerializer(self.profile)
        self.assertEqual(set(serializer.data.keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at',
        })

    def test_business_list_serializer_fields_are_exact(self):
        serializer = BusinessProfileListSerializer(self.profile)
        self.assertEqual(set(serializer.data.keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
        })

    def test_customer_list_serializer_fields_are_exact(self):
        serializer = CustomerProfileListSerializer(self.profile)
        self.assertEqual(set(serializer.data.keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'uploaded_at',
            'type',
        })

    def test_related_user_fields_are_exposed_correctly(self):
        serializer = ProfileDetailSerializer(self.profile)
        self.assertEqual(serializer.data['username'], self.user.username)
        self.assertEqual(serializer.data['first_name'], self.user.first_name)
        self.assertEqual(serializer.data['last_name'], self.user.last_name)
        self.assertEqual(serializer.data['email'], self.user.email)

    def test_nullable_text_values_return_empty_strings(self):
        self.user.first_name = None
        self.user.last_name = None
        self.profile.location = None
        self.profile.tel = None
        self.profile.description = None
        self.profile.working_hours = None
        serializer = ProfileDetailSerializer(self.profile)
        for field in ProfileDetailSerializer.empty_string_fields:
            self.assertEqual(serializer.data[field], '')

    def test_detail_serializer_can_update_user_fields(self):
        serializer = ProfileDetailSerializer(
            self.profile,
            data={
                'first_name': 'Updated',
                'last_name': 'Name',
                'email': 'updated@mail.de',
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'updated@mail.de')

    def test_detail_serializer_can_update_profile_fields(self):
        serializer = ProfileDetailSerializer(
            self.profile,
            data={
                'location': 'Hamburg',
                'tel': '654321',
                'description': 'Updated description',
                'working_hours': '10-6',
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.location, 'Hamburg')
        self.assertEqual(self.profile.tel, '654321')
        self.assertEqual(self.profile.description, 'Updated description')
        self.assertEqual(self.profile.working_hours, '10-6')


class ProfileDetailViewTests(APITestCase):
    """Tests for the profile detail endpoint."""

    def test_business_user_can_retrieve_own_profile(self):
        user, profile = self._create_user_with_profile(Profile.BUSINESS)
        self.client.force_authenticate(user=user)
        response = self.client.get(self._url(user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], profile.type)

    def test_customer_user_can_retrieve_own_profile(self):
        user, profile = self._create_user_with_profile(Profile.CUSTOMER)
        self.client.force_authenticate(user=user)
        response = self.client.get(self._url(user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], profile.type)

    def test_authenticated_user_can_retrieve_another_users_profile(self):
        auth_user, _ = self._create_user_with_profile(Profile.CUSTOMER)
        other_user, _ = self._create_user_with_profile(Profile.BUSINESS)
        self.client.force_authenticate(user=auth_user)
        response = self.client.get(self._url(other_user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], other_user.id)

    def test_response_fields_are_exact(self):
        user, _ = self._create_user_with_profile(Profile.BUSINESS)
        self.client.force_authenticate(user=user)
        response = self.client.get(self._url(user.id))
        self.assertEqual(set(response.data.keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at',
        })

    def test_empty_text_fields_are_returned_as_empty_strings(self):
        user, profile = self._create_user_with_profile(Profile.BUSINESS)
        self._set_nullable_values(user, profile)
        self.client.force_authenticate(user=user)
        response = self.client.get(self._url(user.id))
        for field in ProfileDetailSerializer.empty_string_fields:
            self.assertEqual(response.data[field], '')

    def test_unauthenticated_request_returns_unauthorized(self):
        user, _ = self._create_user_with_profile(Profile.BUSINESS)
        response = self.client.get(self._url(user.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_id_returns_not_found(self):
        user, _ = self._create_user_with_profile(Profile.BUSINESS)
        self.client.force_authenticate(user=user)
        response = self.client.get(self._url(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_endpoint_uses_user_id_not_profile_id(self):
        auth_user = User.objects.create_user(username='noProfile')
        target_user, profile = self._create_user_with_profile(Profile.BUSINESS)
        self.client.force_authenticate(user=auth_user)
        self.assertNotEqual(target_user.id, profile.id)
        response = self.client.get(self._url(target_user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], target_user.id)

    def _create_user_with_profile(self, profile_type):
        user = User.objects.create_user(
            username=f'user{User.objects.count()}',
            email='user@mail.de',
        )
        profile = Profile.objects.create(user=user, type=profile_type)
        return user, profile

    def _set_nullable_values(self, user, profile):
        user.first_name = ''
        user.last_name = ''
        user.save()
        profile.location = ''
        profile.tel = ''
        profile.description = ''
        profile.working_hours = ''
        profile.save()

    def _url(self, user_id):
        return reverse('profile_app:profile-detail', kwargs={'pk': user_id})


class ProfilePatchViewTests(APITestCase):
    """Tests for profile detail partial updates."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='owner',
            email='owner@mail.de',
            first_name='Old',
            last_name='Owner',
        )
        self.profile = Profile.objects.create(
            user=self.user,
            type=Profile.BUSINESS,
            location='Berlin',
            tel='123',
            description='Old description',
            working_hours='9-5',
        )
        self.url = reverse(
            'profile_app:profile-detail',
            kwargs={'pk': self.user.id},
        )

    def test_owner_can_patch_own_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {'location': 'Hamburg'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_first_name_updates(self):
        self._patch_as_owner({'first_name': 'New'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'New')

    def test_last_name_updates(self):
        self._patch_as_owner({'last_name': 'Name'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, 'Name')

    def test_email_updates(self):
        self._patch_as_owner({'email': 'new@mail.de'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@mail.de')

    def test_location_updates(self):
        self._patch_as_owner({'location': 'Cologne'})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.location, 'Cologne')

    def test_tel_updates(self):
        self._patch_as_owner({'tel': '456'})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.tel, '456')

    def test_description_updates(self):
        self._patch_as_owner({'description': 'New description'})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.description, 'New description')

    def test_working_hours_updates(self):
        self._patch_as_owner({'working_hours': '10-6'})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.working_hours, '10-6')

    def test_partial_patch_works(self):
        response = self._patch_as_owner({'location': 'Munich'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location'], 'Munich')

    def test_full_detailed_response_is_returned(self):
        response = self._patch_as_owner({'location': 'Munich'})
        self.assertEqual(set(response.data.keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
            'email',
            'created_at',
        })

    def test_another_authenticated_user_gets_forbidden(self):
        other = User.objects.create_user(username='other')
        self.client.force_authenticate(user=other)
        response = self.client.patch(
            self.url,
            {'location': 'Munich'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_gets_unauthorized(self):
        response = self.client.patch(
            self.url,
            {'location': 'Munich'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_id_gets_not_found(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse('profile_app:profile-detail', kwargs={'pk': 999}),
            {'location': 'Munich'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_email_gets_bad_request(self):
        response = self._patch_as_owner({'email': 'invalid-email'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_cannot_be_changed(self):
        self._patch_as_owner({'username': 'changed'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'owner')

    def test_type_cannot_be_changed(self):
        self._patch_as_owner({'type': Profile.CUSTOMER})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.type, Profile.BUSINESS)

    def test_user_cannot_be_changed(self):
        other = User.objects.create_user(username='other')
        self._patch_as_owner({'user': other.id})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.user, self.user)

    def test_created_at_cannot_be_changed(self):
        original_created_at = self.profile.created_at
        self._patch_as_owner({'created_at': '2000-01-01T00:00:00Z'})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.created_at, original_created_at)

    def _patch_as_owner(self, data):
        self.client.force_authenticate(user=self.user)
        return self.client.patch(self.url, data, format='json')


class BusinessProfileListViewTests(APITestCase):
    """Tests for the business profile list endpoint."""

    def setUp(self):
        self.url = reverse('profile_app:business-profile-list')
        self.user = User.objects.create_user(username='viewer')

    def test_authenticated_user_gets_ok(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_business_profiles_are_returned(self):
        business = self._create_profile('businessUser', Profile.BUSINESS)
        self._create_profile('customerUser', Profile.CUSTOMER)
        response = self._get_as_authenticated_user()
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user'], business.user.id)

    def test_customer_profiles_are_excluded(self):
        self._create_profile('customerUser', Profile.CUSTOMER)
        response = self._get_as_authenticated_user()
        self.assertEqual(response.data, [])

    def test_response_fields_are_exact(self):
        self._create_profile('businessUser', Profile.BUSINESS)
        response = self._get_as_authenticated_user()
        self.assertEqual(set(response.data[0].keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'location',
            'tel',
            'description',
            'working_hours',
            'type',
        })

    def test_empty_text_fields_are_returned_as_empty_strings(self):
        self._create_profile('businessUser', Profile.BUSINESS)
        response = self._get_as_authenticated_user()
        for field in BusinessProfileListSerializer.empty_string_fields:
            self.assertEqual(response.data[0][field], '')

    def test_multiple_business_profiles_are_returned(self):
        self._create_profile('firstBusiness', Profile.BUSINESS)
        self._create_profile('secondBusiness', Profile.BUSINESS)
        response = self._get_as_authenticated_user()
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_request_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def _create_profile(self, username, profile_type):
        user = User.objects.create_user(username=username)
        return Profile.objects.create(user=user, type=profile_type)

    def _get_as_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        return self.client.get(self.url)


class CustomerProfileListViewTests(APITestCase):
    """Tests for the customer profile list endpoint."""

    def setUp(self):
        self.url = reverse('profile_app:customer-profile-list')
        self.user = User.objects.create_user(username='viewer')

    def test_authenticated_user_gets_ok(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_customer_profiles_are_returned(self):
        customer = self._create_profile('customerUser', Profile.CUSTOMER)
        self._create_profile('businessUser', Profile.BUSINESS)
        response = self._get_as_authenticated_user()
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user'], customer.user.id)

    def test_business_profiles_are_excluded(self):
        self._create_profile('businessUser', Profile.BUSINESS)
        response = self._get_as_authenticated_user()
        self.assertEqual(response.data, [])

    def test_response_fields_are_exact(self):
        self._create_profile('customerUser', Profile.CUSTOMER)
        response = self._get_as_authenticated_user()
        self.assertEqual(set(response.data[0].keys()), {
            'user',
            'username',
            'first_name',
            'last_name',
            'file',
            'uploaded_at',
            'type',
        })

    def test_uploaded_at_is_returned(self):
        self._create_profile('customerUser', Profile.CUSTOMER)
        response = self._get_as_authenticated_user()
        self.assertTrue(response.data[0]['uploaded_at'])

    def test_multiple_customer_profiles_are_returned(self):
        self._create_profile('firstCustomer', Profile.CUSTOMER)
        self._create_profile('secondCustomer', Profile.CUSTOMER)
        response = self._get_as_authenticated_user()
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_request_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def _create_profile(self, username, profile_type):
        user = User.objects.create_user(username=username)
        return Profile.objects.create(user=user, type=profile_type)

    def _get_as_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        return self.client.get(self.url)
