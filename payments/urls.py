from django.urls import path
from . import views

urlpatterns = [

    # Admin payment management
    path(
        '',
        views.payment_list,
        name='payment_list'
    ),

    path(
        'add/',
        views.add_payment,
        name='add_payment'
    ),

    path(
        'approve/<int:payment_id>/',
        views.approve_payment,
        name='approve_payment'
    ),

    path(
        'reject/<int:payment_id>/',
        views.reject_payment,
        name='reject_payment'
    ),

    # Tenant payment history
    path(
        'tenant-history/',
        views.tenant_payment_history,
        name='tenant_payment_history'
    ),

    # Tenant rent statement
    path(
        'tenant-statement/',
        views.tenant_rent_statement,
        name='tenant_rent_statement'
    ),

    # Download PDF
    path(
        'download-statement/',
        views.download_rent_statement_pdf,
        name='download_rent_statement_pdf'
    ),
]