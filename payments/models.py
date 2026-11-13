
from django.db import models
from tenants.models import Tenant


class Payment(models.Model):

    PAYMENT_TYPES = [
        ('rent', 'Monthly Rent'),
        ('water', 'Water Bill'),
        ('garbage', 'Garbage Collection'),
        ('deposit', 'Security Deposit'),
        ('other', 'Other Charges'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('other', 'Other'),
    ]

    PAYMENT_STATUS = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='rent'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_date = models.DateField()

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash'
    )

    transaction_code = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='paid'
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.tenant.tenant_user.username} - "
            f"{self.get_payment_type_display()} - "
            f"KES {self.amount}"
        )
