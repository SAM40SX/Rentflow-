from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'tenant',
        'amount',
        'payment_date',
        'payment_method',
        'status',
        'transaction_code',
    )

    list_filter = (
        'status',
        'payment_method',
        'payment_date',
    )

    search_fields = (
        'tenant__tenant_user__username',
        'transaction_code',
    )