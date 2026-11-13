
from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from accounts.models import SystemSettings
from notifications.models import Notification
from .models import RentReminder
from tenants.models import Tenant


@login_required
def reminder_list(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    reminders = RentReminder.objects.select_related(
        'tenant',
        'tenant__tenant_user',
        'tenant__property'
    ).order_by('-created_at')

    return render(
        request,
        'reminders/reminder_list.html',
        {'reminders': reminders}
    )


@login_required
def generate_reminders(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    today = timezone.localdate()

    # Get the rent due day from System Settings
    settings = SystemSettings.objects.filter(pk=1).first()

    due_day = settings.rent_due_day if settings else 10

    # Build this month's rent due date
    due_date = today.replace(day=due_day)

    # Determine reminder status
    if today < due_date:
        reminder_type = 'upcoming'
    elif today == due_date:
        reminder_type = 'due'
    else:
        reminder_type = 'overdue'

    tenants = Tenant.objects.filter(
        is_active=True,
        tenant_user__is_active=True,
        tenant_user__is_active_account=True
    )

    created_count = 0
    updated_count = 0
    paid_count = 0
    notification_count = 0

    for tenant in tenants:

        # Count ONLY paid monthly rent payments.
        # Water, garbage, deposits and other charges are excluded.
        payment_total = tenant.payments.filter(
            payment_type='rent',
            status='paid',
            payment_date__year=today.year,
            payment_date__month=today.month
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Calculate outstanding monthly rent
        balance = max(
            tenant.monthly_rent - payment_total,
            Decimal('0.00')
        )

        # Exclude fully paid tenants
        if balance == Decimal('0.00'):

            RentReminder.objects.filter(
                tenant=tenant,
                reminder_date=due_date
            ).delete()

            paid_count += 1
            continue

        formatted_due_date = due_date.strftime('%d %B %Y')

        reminder_message = (
            f"Hello {tenant.tenant_user.username}, "
            f"your monthly rent is KES {tenant.monthly_rent}. "
            f"You have paid KES {payment_total}. "
            f"Your remaining rent balance is KES {balance}, "
            f"due on {formatted_due_date}."
        )

        # Create or update rent reminder
        reminder, created = RentReminder.objects.get_or_create(
            tenant=tenant,
            reminder_date=due_date,
            defaults={
                'reminder_type': reminder_type,
                'message': reminder_message,
                'status': 'pending',
            }
        )

        if created:
            created_count += 1

        else:
            reminder.reminder_type = reminder_type
            reminder.message = reminder_message

            reminder.save(
                update_fields=[
                    'reminder_type',
                    'message'
                ]
            )

            updated_count += 1

        # Find an existing unread rent notification
        notification = Notification.objects.filter(
            user=tenant.tenant_user,
            title="Monthly Rent Reminder",
            notification_type='rent',
            is_read=False
        ).order_by('-created_at').first()

        if notification:

            notification.message = reminder_message

            notification.save(
                update_fields=['message']
            )

        else:

            Notification.objects.create(
                user=tenant.tenant_user,
                title="Monthly Rent Reminder",
                message=reminder_message,
                notification_type='rent'
            )

        notification_count += 1

    messages.success(
        request,
        f'Reminder generation complete. '
        f'{created_count} new reminders created, '
        f'{updated_count} updated, '
        f'{notification_count} tenant notifications created or updated, '
        f'{paid_count} fully paid tenants excluded.'
    )

    return redirect('reminder_list')
