from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Coderr-specific profile data for a Django user account."""

    CUSTOMER = 'customer'
    BUSINESS = 'business'

    PROFILE_TYPE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (BUSINESS, 'Business'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    file = models.FileField(upload_to='profiles/', blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    tel = models.CharField(max_length=50, blank=True, default='')
    description = models.TextField(blank=True, default='')
    working_hours = models.CharField(max_length=255, blank=True, default='')
    type = models.CharField(max_length=20, choices=PROFILE_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__username']
        verbose_name = 'profile'
        verbose_name_plural = 'profiles'

    def __str__(self):
        return f'{self.user.username} ({self.type})'
