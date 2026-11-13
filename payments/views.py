
from io import BytesIO
from datetime import date
from decimal import Decimal

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from .models import Payment
from .forms import PaymentForm
from accounts.models import SystemSettings
from notifications.models import Notification


# =====================================================
# HELPER: GET MONTHLY RENT PAID
# =====================================================

def get_monthly_rent_paid(tenant, year, month):

    return tenant.payments.filter(
        payment_type='rent',
        status='paid',
        payment_date__year=year,
        payment_date__month=month
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')


# =====================================================
# HELPER: GET REMAINING MONTHLY RENT
# =====================================================

def get_monthly_rent_balance(tenant, payment_date):

    paid_amount = get_monthly_rent_paid(
        tenant,
        payment_date.year,
        payment_date.month
    )

    return max(
        tenant.monthly_rent - paid_amount,
        Decimal('0.00')
    )


# =====================================================
# PAYMENT LIST
# =====================================================

@login_required
def payment_list(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    payments = Payment.objects.select_related(
        'tenant',
        'tenant__tenant_user',
        'tenant__property'
    )

    search_query = request.GET.get('search', '').strip()

    if search_query:
        payments = payments.filter(
            Q(tenant__tenant_user__username__icontains=search_query) |
            Q(tenant__tenant_user__first_name__icontains=search_query) |
            Q(tenant__tenant_user__last_name__icontains=search_query)
        )

    status_filter = request.GET.get('status', '')

    if status_filter in ['paid', 'pending', 'failed']:
        payments = payments.filter(status=status_filter)

    payments = payments.order_by(
        '-payment_date',
        '-created_at'
    )

    total_collected = payments.filter(
        status='paid'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    total_pending = payments.filter(
        status='pending'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    context = {
        'payments': payments,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'paid_count': payments.filter(status='paid').count(),
        'pending_count': payments.filter(status='pending').count(),
        'failed_count': payments.filter(status='failed').count(),
        'search_query': search_query,
        'status_filter': status_filter,
    }

    return render(
        request,
        'payments/payment_list.html',
        context
    )


# =====================================================
# ADD PAYMENT
# =====================================================

@login_required
def add_payment(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method == 'POST':

        form = PaymentForm(request.POST)

        if form.is_valid():

            payment = form.save()
            tenant = payment.tenant

            if payment.status == 'paid':

                if payment.payment_type == 'rent':

                    balance = get_monthly_rent_balance(
                        tenant,
                        payment.payment_date
                    )

                    notification_title = "Rent Payment Confirmation"

                    notification_message = (
                        f"Hello {tenant.tenant_user.username}, "
                        f"your rent payment of KES {payment.amount:,.2f} "
                        f"has been received successfully. "
                        f"Payment date: {payment.payment_date}. "
                        f"Payment method: "
                        f"{payment.get_payment_method_display()}. "
                        f"Your remaining rent balance for this month is "
                        f"KES {balance:,.2f}."
                    )

                else:

                    notification_title = "Payment Confirmation"

                    notification_message = (
                        f"Hello {tenant.tenant_user.username}, "
                        f"your payment of KES {payment.amount:,.2f} "
                        f"for {payment.get_payment_type_display()} "
                        f"has been received successfully. "
                        f"Payment date: {payment.payment_date}. "
                        f"Payment method: "
                        f"{payment.get_payment_method_display()}."
                    )

                Notification.objects.create(
                    user=tenant.tenant_user,
                    title=notification_title,
                    message=notification_message,
                    notification_type='payment'
                )

            messages.success(
                request,
                'Payment recorded successfully.'
            )

            return redirect('payment_list')

    else:
        form = PaymentForm()

    return render(
        request,
        'payments/add_payment.html',
        {'form': form}
    )


# =====================================================
# TENANT PAYMENT HISTORY
# =====================================================

@login_required
def tenant_payment_history(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    tenant = getattr(
        request.user,
        'tenant_profile',
        None
    )

    if not tenant:

        return render(
            request,
            'payments/tenant_payment_history.html',
            {
                'payments': [],
                'total_paid': Decimal('0.00'),
                'tenant_name': request.user.username,
            }
        )

    payments = Payment.objects.filter(
        tenant=tenant
    ).order_by(
        '-payment_date',
        '-created_at'
    )

    total_paid = payments.filter(
        status='paid'
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    context = {
        'payments': payments,
        'total_paid': total_paid,
        'tenant_name': request.user.username,
    }

    return render(
        request,
        'payments/tenant_payment_history.html',
        context
    )


# =====================================================
# TENANT RENT STATEMENT
# =====================================================

@login_required
def tenant_rent_statement(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    tenant = getattr(
        request.user,
        'tenant_profile',
        None
    )

    today = timezone.localdate()

    settings = SystemSettings.objects.filter(
        pk=1
    ).first()

    rent_due_day = (
        settings.rent_due_day
        if settings
        else 10
    )

    statement = []

    total_rent = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_balance = Decimal('0.00')

    if tenant:

        # First rent charge is the month after move-in.
        start_year = tenant.move_in_date.year
        start_month = tenant.move_in_date.month + 1

        if start_month > 12:
            start_month = 1
            start_year += 1

        year = start_year
        month = start_month

        while (year, month) <= (today.year, today.month):

            due_date = date(
                year,
                month,
                rent_due_day
            )

            # Only paid RENT payments reduce rent.
            paid_amount = get_monthly_rent_paid(
                tenant,
                year,
                month
            )

            monthly_rent = tenant.monthly_rent

            monthly_balance = max(
                monthly_rent - paid_amount,
                Decimal('0.00')
            )

            if paid_amount >= monthly_rent:
                payment_status = 'Paid'

            elif paid_amount > 0:
                payment_status = 'Partially Paid'

            elif today > due_date:
                payment_status = 'Overdue'

            else:
                payment_status = 'Pending'

            statement.append({
                'month': due_date.strftime('%B %Y'),
                'due_date': due_date,
                'rent': monthly_rent,
                'paid': paid_amount,
                'balance': monthly_balance,
                'status': payment_status,
            })

            total_rent += monthly_rent
            total_paid += paid_amount
            total_balance += monthly_balance

            month += 1

            if month > 12:
                month = 1
                year += 1

    context = {
        'tenant_name': request.user.username,
        'tenant': tenant,
        'statement': statement,
        'total_rent': total_rent,
        'total_paid': total_paid,
        'total_balance': total_balance,
    }

    return render(
        request,
        'payments/tenant_rent_statement.html',
        context
    )


# =====================================================
# DOWNLOAD RENT STATEMENT PDF
# =====================================================

@login_required
def download_rent_statement_pdf(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    tenant = getattr(
        request.user,
        'tenant_profile',
        None
    )

    if not tenant:
        return HttpResponse(
            "No property has been assigned to your account."
        )

    today = timezone.localdate()

    settings = SystemSettings.objects.filter(
        pk=1
    ).first()

    rent_due_day = (
        settings.rent_due_day
        if settings
        else 10
    )

    statement = []

    total_rent = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_balance = Decimal('0.00')

    # First rent charge is the month after move-in.
    year = tenant.move_in_date.year
    month = tenant.move_in_date.month + 1

    if month > 12:
        month = 1
        year += 1

    while (year, month) <= (today.year, today.month):

        due_date = date(
            year,
            month,
            rent_due_day
        )

        # Only paid RENT payments reduce rent.
        paid_amount = get_monthly_rent_paid(
            tenant,
            year,
            month
        )

        monthly_rent = tenant.monthly_rent

        monthly_balance = max(
            monthly_rent - paid_amount,
            Decimal('0.00')
        )

        if paid_amount >= monthly_rent:
            status = 'Paid'

        elif paid_amount > 0:
            status = 'Partially Paid'

        elif today > due_date:
            status = 'Overdue'

        else:
            status = 'Pending'

        statement.append([
            due_date.strftime('%B %Y'),
            due_date.strftime('%d %b %Y'),
            f"KES {monthly_rent:,.2f}",
            f"KES {paid_amount:,.2f}",
            f"KES {monthly_balance:,.2f}",
            status
        ])

        total_rent += monthly_rent
        total_paid += paid_amount
        total_balance += monthly_balance

        month += 1

        if month > 12:
            month = 1
            year += 1

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "<b>RENTFLOW</b>",
            styles['Title']
        )
    )

    elements.append(
        Paragraph(
            "TENANT RENT STATEMENT",
            styles['Heading2']
        )
    )

    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            f"<b>Tenant:</b> "
            f"{request.user.get_full_name() or request.user.username}",
            styles['Normal']
        )
    )

    elements.append(
        Paragraph(
            f"<b>Statement Date:</b> "
            f"{today.strftime('%d %B %Y')}",
            styles['Normal']
        )
    )

    due_suffix = (
        'st' if rent_due_day == 1
        else 'nd' if rent_due_day == 2
        else 'rd' if rent_due_day == 3
        else 'th'
    )

    elements.append(
        Paragraph(
            f"<b>Rent Due Date:</b> "
            f"{rent_due_day}{due_suffix} of every month",
            styles['Normal']
        )
    )

    elements.append(Spacer(1, 20))

    summary_data = [
        ['TOTAL RENT', 'TOTAL RENT PAID', 'OUTSTANDING'],
        [
            f"KES {total_rent:,.2f}",
            f"KES {total_paid:,.2f}",
            f"KES {total_balance:,.2f}"
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[175, 175, 175]
    )

    summary_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#E2E8F0')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#0F172A')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
        ])
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 25))

    elements.append(
        Paragraph(
            "<b>MONTHLY RENT BREAKDOWN</b>",
            styles['Heading2']
        )
    )

    elements.append(Spacer(1, 10))

    table_data = [
        [
            'Month',
            'Due Date',
            'Rent',
            'Paid',
            'Balance',
            'Status'
        ]
    ]

    table_data.extend(statement)

    rent_table = Table(
        table_data,
        colWidths=[85, 70, 85, 85, 85, 65],
        repeatRows=1
    )

    rent_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
                colors.white,
                colors.HexColor('#F1F5F9')
            ]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(rent_table)
    elements.append(Spacer(1, 25))

    elements.append(
        Paragraph(
            "Generated by RentFlow. This statement reflects "
            "successful paid RENT payments only. Water bills, "
            "garbage collection fees and security deposits are "
            "excluded from rent calculations.",
            styles['Italic']
        )
    )

    document.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(
        pdf,
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        'attachment; filename="RentFlow_Rent_Statement.pdf"'
    )

    return response


# =====================================================
# APPROVE PAYMENT
# =====================================================

@login_required
def approve_payment(request, payment_id):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method != 'POST':
        return redirect('payment_list')

    payment = get_object_or_404(
        Payment,
        id=payment_id
    )

    if payment.status != 'pending':

        messages.warning(
            request,
            'Only pending payments can be approved.'
        )

        return redirect('payment_list')

    payment.status = 'paid'
    payment.save(update_fields=['status'])

    tenant = payment.tenant

    if payment.payment_type == 'rent':

        balance = get_monthly_rent_balance(
            tenant,
            payment.payment_date
        )

        notification_title = 'Rent Payment Approved'

        notification_message = (
            f'Your rent payment of KES {payment.amount:,.2f} '
            f'has been approved successfully. '
            f'Your remaining monthly rent balance is '
            f'KES {balance:,.2f}.'
        )

    else:

        notification_title = 'Payment Approved'

        notification_message = (
            f'Your payment of KES {payment.amount:,.2f} '
            f'for {payment.get_payment_type_display()} '
            f'has been approved successfully.'
        )

    Notification.objects.create(
        user=tenant.tenant_user,
        title=notification_title,
        message=notification_message,
        notification_type='payment'
    )

    messages.success(
        request,
        'Payment approved successfully.'
    )

    return redirect('payment_list')


# =====================================================
# REJECT PAYMENT
# =====================================================

@login_required
def reject_payment(request, payment_id):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method != 'POST':
        return redirect('payment_list')

    payment = get_object_or_404(
        Payment,
        id=payment_id
    )

    if payment.status != 'pending':

        messages.warning(
            request,
            'Only pending payments can be rejected.'
        )

        return redirect('payment_list')

    payment.status = 'failed'
    payment.save(update_fields=['status'])

    Notification.objects.create(
        user=payment.tenant.tenant_user,
        title='Payment Rejected',
        message=(
            f'Your payment of KES {payment.amount:,.2f} '
            f'dated {payment.payment_date} was not approved. '
            f'Please contact the administrator for assistance.'
        ),
        notification_type='payment'
    )

    messages.success(
        request,
        'Payment rejected successfully.'
    )

    return redirect('payment_list')
