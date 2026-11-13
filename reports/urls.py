
from django.urls import path
from . import views
from . import pdf_views

urlpatterns = [
    # Reports dashboard
    path(
        '',
        views.reports_dashboard,
        name='reports_dashboard'
    ),

    # PDF downloads
    path(
        'pdf/monthly-collection/',
        pdf_views.monthly_collection_pdf,
        name='monthly_collection_pdf'
    ),

    path(
        'pdf/outstanding-rent/',
        pdf_views.outstanding_rent_pdf,
        name='outstanding_rent_pdf'
    ),

    path(
        'pdf/tenant-payment-history/',
        pdf_views.tenant_payment_history_pdf,
        name='tenant_payment_history_pdf'
    ),

    path(
        'pdf/property-occupancy/',
        pdf_views.property_occupancy_pdf,
        name='property_occupancy_pdf'
    ),
]
