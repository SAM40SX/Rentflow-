
from django.contrib import admin
from .models import RentReminder


@admin.register(RentReminder)
class RentReminderAdmin(admin.ModelAdmin):
    list_display = (
        'tenant',
        'reminder_type',
        'reminder_date',
        'status',
        'created_at',
    )

    list_filter = ('reminder_type', 'status', 'reminder_date')

    search_fields = (
        'tenant__tenant_user__username',
        'message',
    )
