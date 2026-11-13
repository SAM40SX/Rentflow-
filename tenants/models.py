
from django.db import models
from accounts.models import User
from properties.models import Property


class Tenant(models.Model):
    tenant_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'tenant'},
        related_name='tenant_profile'
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name='tenants'
    )

    move_in_date = models.DateField()
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant_user.username} - {self.property.name}"
