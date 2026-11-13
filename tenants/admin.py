from django.contrib import admin
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        'tenant_user',
        'property',
        'move_in_date',
        'monthly_rent',
        'deposit_amount',
        'is_active',
    )

    list_filter = ('is_active', 'move_in_date')
    search_fields = ('tenant_user__username', 'property__name')