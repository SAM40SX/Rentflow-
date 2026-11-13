
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from payments.models import Payment
from tenants.models import Tenant
from properties.models import Property


# =========================================
# COMMON PDF GENERATOR
# =========================================

def create_pdf_response(title, filename, table_data, note=None):

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{filename}"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0A192F'),
        fontSize=18,
        spaceAfter=8,
    )

    normal_style = styles['Normal']

    elements = [
        Paragraph('RentFlow', title_style),
        Paragraph(title, styles['Heading2']),
        Paragraph(
            f"Generated on: {timezone.localdate().strftime('%d %B %Y')}",
            normal_style
        ),
        Spacer(1, 12),
    ]

    if note:
        elements.append(
            Paragraph(note, normal_style)
        )
        elements.append(Spacer(1, 10))

    if not table_data or len(table_data) == 1:

        elements.append(
            Paragraph(
                'No records found for this report.',
                normal_style
            )
        )

    else:

        report_table = Table(
            table_data,
            repeatRows=1,
            hAlign='LEFT'
        )

        report_table.setStyle(
            TableStyle([
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, 0),
                    colors.HexColor('#0A192F')
                ),
                (
                    'TEXTCOLOR',
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    'FONTNAME',
                    (0, 0),
                    (-1, 0),
                    'Helvetica-Bold'
                ),
                (
                    'FONTSIZE',
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor('#D1D5DB')
                ),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor('#F3F4F6')
                    ]
                ),
                (
                    'VALIGN',
                    (0, 0),
                    (-1, -1),
                    'MIDDLE'
                ),
                (
                    'LEFTPADDING',
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    'RIGHTPADDING',
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    'TOPPADDING',
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    'BOTTOMPADDING',
                    (0, 0),
                    (-1, -1),
                    7
                ),
            ])
        )

        elements.append(report_table)

    document.build(elements)

    return response


# =========================================
# ADMIN ACCESS CHECK
# =========================================

def is_admin(request):

    return request.user.role == 'admin'


# =========================================
# 1. MONTHLY COLLECTION PDF
# =========================================

@login_required
def monthly_collection_pdf(request):

    if not is_admin(request):
        return HttpResponseForbidden(
            'Access denied. Administrators only.'
        )

    today = timezone.localdate()

    default_start_date = today.replace(day=1)
    default_end_date = today

    start_date = default_start_date
    end_date = default_end_date

    start_date_input = request.GET.get('start_date', '')
    end_date_input = request.GET.get('end_date', '')

    try:

        if start_date_input:
            start_date = date.fromisoformat(
                start_date_input
            )

        if end_date_input:
            end_date = date.fromisoformat(
                end_date_input
            )

        if (
            start_date > end_date
            or end_date > today
        ):
            start_date = default_start_date
            end_date = default_end_date

    except (ValueError, TypeError):

        start_date = default_start_date
        end_date = default_end_date

    payments = Payment.objects.filter(
        status='paid',
        payment_date__range=(
            start_date,
            end_date
        )
    ).select_related(
        'tenant',
        'tenant__tenant_user'
    ).order_by(
        'payment_date',
        'created_at'
    )

    table_data = [[
        'Tenant',
        'Date',
        'Amount (KES)',
        'Method',
        'Transaction Code',
    ]]

    for payment in payments:

        table_data.append([
            payment.tenant.tenant_user.username,
            payment.payment_date.strftime('%d %b %Y'),
            f'{payment.amount:,.2f}',
            payment.get_payment_method_display(),
            payment.transaction_code or '-',
        ])

    total = payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    if payments.exists():

        table_data.append([
            'TOTAL',
            '',
            f'{total:,.2f}',
            '',
            '',
        ])

    return create_pdf_response(
        title=(
            'Collection Report - '
            f'{start_date.strftime("%d %b %Y")} '
            'to '
            f'{end_date.strftime("%d %b %Y")}'
        ),
        filename='rentflow_monthly_collection.pdf',
        table_data=table_data,
        note=(
            f'Report period: {start_date.strftime("%d %B %Y")} '
            f'to {end_date.strftime("%d %B %Y")}. '
            'Only successfully paid transactions are included.'
        ),
    )


# =========================================
# 2. OUTSTANDING RENT PDF
# =========================================

@login_required
def outstanding_rent_pdf(request):

    if not is_admin(request):
        return HttpResponseForbidden(
            'Access denied. Administrators only.'
        )

    today = timezone.localdate()

    # Read the selected end date from the dashboard.

    end_date_input = request.GET.get('end_date', '')

    report_date = today

    try:

        if end_date_input:
            report_date = date.fromisoformat(
                end_date_input
            )

        if report_date > today:
            raise ValueError

    except (ValueError, TypeError):

        report_date = today

    active_tenants = Tenant.objects.filter(
        is_active=True
    ).select_related(
        'tenant_user',
        'property'
    )

    table_data = [[
        'Tenant',
        'Property',
        'Monthly Rent (KES)',
        'Rent Due (KES)',
        'Paid (KES)',
        'Balance (KES)',
    ]]

    total_outstanding = Decimal('0.00')

    # Rent is due on the 10th of every month.

    current_month = (
        report_date.year * 12 + report_date.month
    )

    if report_date.day >= 10:

        last_due_month = current_month

    else:

        last_due_month = current_month - 1

    for tenant in active_tenants:

        # First full rent starts the month
        # after the tenant moves in.

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

        # Only paid transactions made on or before
        # the selected reporting date are counted.

        paid_amount = Payment.objects.filter(
            tenant=tenant,
            payment_type='rent',
            status='paid',
            payment_date__lte=report_date,
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        balance = rent_due - paid_amount

        if balance > 0:

            total_outstanding += balance

            table_data.append([
                tenant.tenant_user.username,
                tenant.property.name,
                f'{tenant.monthly_rent:,.2f}',
                f'{rent_due:,.2f}',
                f'{paid_amount:,.2f}',
                f'{balance:,.2f}',
            ])

    if len(table_data) > 1:

        table_data.append([
            'TOTAL',
            '',
            '',
            '',
            '',
            f'{total_outstanding:,.2f}',
        ])

    return create_pdf_response(
        title=(
            'Outstanding Rent Report - '
            f'As at {report_date.strftime("%d %b %Y")}'
        ),
        filename='rentflow_outstanding_rent.pdf',
        table_data=table_data,
       note=(
    f'Outstanding rent calculated as at '
    f'{report_date.strftime("%d %B %Y")}. '
    'Rent is due on the configured monthly due date. '
    'The first full rent month is the month after move-in. '
    'Only paid monthly rent transactions made on or before '
    'the report date are counted. Water bills, garbage fees, '
    'security deposits and other charges are excluded.'
),
    )


# =========================================
# 3. TENANT PAYMENT HISTORY PDF
# =========================================

@login_required
def tenant_payment_history_pdf(request):

    if not is_admin(request):
        return HttpResponseForbidden(
            'Access denied. Administrators only.'
        )

    payments = Payment.objects.select_related(
        'tenant',
        'tenant__tenant_user',
        'tenant__property'
    ).order_by(
        'tenant__tenant_user__username',
        '-payment_date'
    )

    tenant_id = request.GET.get('tenant_id')

    if tenant_id:

        if not tenant_id.isdigit():

            return HttpResponse(
                'Invalid tenant ID.',
                status=400
            )

        payments = payments.filter(
            tenant_id=int(tenant_id)
        )

    table_data = [[
        'Tenant',
        'Property',
        'Date',
        'Amount (KES)',
        'Method',
        'Status',
        'Transaction Code',
    ]]

    for payment in payments:

        table_data.append([
            payment.tenant.tenant_user.username,
            payment.tenant.property.name,
            payment.payment_date.strftime('%d %b %Y'),
            f'{payment.amount:,.2f}',
            payment.get_payment_method_display(),
            payment.get_status_display(),
            payment.transaction_code or '-',
        ])

    filename = 'rentflow_tenant_payment_history.pdf'

    return create_pdf_response(
        title='Tenant Payment History',
        filename=filename,
        table_data=table_data,
    )


# =========================================
# 4. PROPERTY OCCUPANCY PDF
# =========================================

@login_required
def property_occupancy_pdf(request):

    if not is_admin(request):
        return HttpResponseForbidden(
            'Access denied. Administrators only.'
        )

    properties = Property.objects.annotate(
        active_tenant_count=Count(
            'tenants',
            filter=Q(tenants__is_active=True),
            distinct=True
        )
    ).order_by('name')

    table_data = [[
        'Property',
        'Type',
        'Location',
        'Active Tenants',
        'Occupancy Status',
    ]]

    for property_item in properties:

        occupied = (
            property_item.active_tenant_count > 0
        )

        table_data.append([
            property_item.name,
            property_item.get_property_type_display(),
            property_item.location,
            str(property_item.active_tenant_count),
            'Occupied' if occupied else 'Vacant',
        ])

    total_properties = properties.count()

    occupied_properties = sum(
        1 for item in properties
        if item.active_tenant_count > 0
    )

    vacant_properties = (
        total_properties - occupied_properties
    )

    if total_properties > 0:

        table_data.append([
            'TOTAL',
            '',
            '',
            '',
            f'{occupied_properties} occupied / {vacant_properties} vacant',
        ])

    return create_pdf_response(
        title='Property Occupancy Report',
        filename='rentflow_property_occupancy.pdf',
        table_data=table_data,
    )
