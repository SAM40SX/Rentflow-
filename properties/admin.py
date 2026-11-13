from django.contrib import admin
from .models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'property_type',
        'location',
        'monthly_rent',
        'owner',
        'created_at',
    )

    list_filter = ('property_type', 'created_at')
    search_fields = ('name', 'location')