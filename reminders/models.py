
from django.db import models
from tenants.models import Tenant


class RentReminder(models.Model):

    REMINDER_TYPES = [
        ('upcoming', 'Upcoming Rent'),
        ('due', 'Rent Due'),
        ('overdue', 'Overdue Rent'),
    ]

    REMINDER_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('read', 'Read'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='rent_reminders'
    )

    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPES,
        default='upcoming'
    )

    message = models.TextField()

    reminder_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=REMINDER_STATUS,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.tenant_user.username} - {self.reminder_type}"
