from django.db import models
from accounts.models import User


class Property(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('bedsitter', 'Bedsitter'),
        ('commercial', 'Commercial'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=150)
    property_type = models.CharField(
        max_length=30,
        choices=PROPERTY_TYPES,
        default='apartment'
    )
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name