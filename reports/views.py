
from datetime import date
from decimal import Decimal
from typing import Any

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Sum
from django.utils import timezone

from payments.models import Payment
from tenants.models import Tenant
from properties.models import Property


@login_required
def reports_dashboard(request):

    # Only administrators can access reports
    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    today = timezone.localdate()

    # =====================================
    # DATE FILTERS
    # =====================================

    default_start_date = today.replace(day=1)
    default_end_date = today

    filter_error = ''

    start_date_input = request.GET.get('start_date', '')
    end_date_input = request.GET.get('end_date', '')

    start_date = default_start_date
    end_date = default_end_date

    try:
        if start_date_input:
            start_date = date.fromisoformat(start_date_input)

        if end_date_input:
            end_date = date.fromisoformat(end_date_input)

        if start_date > end_date:
            raise ValueError

        if end_date > today:
            raise ValueError

    except ValueError:
        start_date = default_start_date
        end_date = default_end_date

        filter_error = (
            'Invalid date range. Please select valid dates '
            'not later than today.'
        )

    # =====================================
    # COLLECTION REPORT
    # =====================================

    paid_payments = Payment.objects.filter(
        status='paid',
        payment_date__lte=today
    )

    period_payments = paid_payments.filter(
        payment_date__range=(start_date, end_date)
    )

    monthly_collection = (
        period_payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    )

    total_collected = (
        paid_payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    )

    # =====================================
    # TENANT RENT BALANCES
    # =====================================

    active_tenants = Tenant.objects.filter(
        is_active=True
    ).select_related(
        'tenant_user',
        'property'
    )

    active_tenants_count = active_tenants.count()

    total_outstanding = Decimal('0.00')
    outstanding_tenants = []

    # Calculate rent outstanding as of selected end date.
    # Rent is due on the 10th of every month.
    # First full rent starts the month after move-in.

    report_date = end_date

    current_month = (
        report_date.year * 12 + report_date.month
    )

    if report_date.day >= 10:
        last_due_month = current_month
    else:
        last_due_month = current_month - 1

    for tenant in active_tenants:

        first_rent_month = (
            tenant.move_in_date.year * 12
            + tenant.move_in_date.month
            + 1
        )

        months_due = max(
            0,
            last_due_month - first_rent_month + 1
        )

        rent_due = (
            tenant.monthly_rent * months_due
        )

        # Only payments made on or before the selected
        # end date are considered.
        paid_amount: Decimal = (
            Payment.objects.filter(
                tenant=tenant,
                payment_type='rent',
                status='paid',
                payment_date__lte=report_date
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
        )

        balance = max(
            Decimal('0.00'),
            rent_due - paid_amount
        )

        total_outstanding += balance

        if balance > 0:
            outstanding_tenants.append({
                'tenant': tenant,
                'rent_due': rent_due,
                'paid': paid_amount,
                'balance': balance,
            })

    # =====================================
    # PROPERTY OCCUPANCY REPORT
    # =====================================

    total_properties = Property.objects.count()

    occupied_properties = Property.objects.filter(
        tenants__is_active=True
    ).distinct().count()

    vacant_properties = (
        total_properties - occupied_properties
    )

    occupancy_rate = (
        (occupied_properties / total_properties) * 100
        if total_properties > 0 else 0
    )

    # =====================================
    # PAYMENT STATUS SUMMARY
    # =====================================

    pending_payments = Payment.objects.filter(
        status='pending'
    ).count()

    failed_payments = Payment.objects.filter(
        status='failed'
    ).count()

    # =====================================
    # RECENT PAYMENT HISTORY
    # =====================================

    recent_payments = Payment.objects.select_related(
        'tenant',
        'tenant__tenant_user',
        'tenant__property'
    ).order_by(
        '-payment_date',
        '-created_at'
    )[:10]

    # =====================================
    # DASHBOARD CONTEXT
    # =====================================

    context = {
        'today': today,

        'monthly_collection': monthly_collection,
        'total_collected': total_collected,

        'start_date': start_date,
        'end_date': end_date,
        'filter_error': filter_error,

        'total_outstanding': total_outstanding,
        'outstanding_tenants': outstanding_tenants,

        'active_tenants_count': active_tenants_count,

        'total_properties': total_properties,
        'occupied_properties': occupied_properties,
        'vacant_properties': vacant_properties,
        'occupancy_rate': occupancy_rate,

        'pending_payments': pending_payments,
        'failed_payments': failed_payments,

        'recent_payments': recent_payments,
    }

    return render(
        request,
        'reports/reports_dashboard.html',
        context
    )
