
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('tenant', 'Tenant'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='tenant'
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    is_active_account = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} - {self.role}"

class SystemSettings(models.Model):
    system_name = models.CharField(
        max_length=150,
        default='RentFlow'
    )

    company_name = models.CharField(
        max_length=150,
        blank=True
    )

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    currency = models.CharField(
        max_length=10,
        default='KES'
    )

    rent_due_day = models.PositiveSmallIntegerField(default=10)

    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.system_name
