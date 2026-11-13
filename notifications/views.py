
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth import get_user_model

from .models import Notification


User = get_user_model()


# ==========================================
# TENANT NOTIFICATION VIEWS
# ==========================================

@login_required
def notification_list(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'notifications/notification_list.html',
        {
            'notifications': notifications,
            'unread_count': notifications.filter(
                is_read=False
            ).count(),
        }
    )


@login_required
def mark_notification_read(request, notification_id):

    if request.method == 'POST':

        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )

        notification.is_read = True
        notification.save(update_fields=['is_read'])

    return redirect('notification_list')


@login_required
def mark_all_notifications_read(request):

    if request.method == 'POST':

        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

    return redirect('notification_list')


# ==========================================
# ADMIN NOTIFICATION MANAGEMENT
# ==========================================

@login_required
def admin_notifications(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    notifications = Notification.objects.select_related(
        'user'
    ).order_by('-created_at')

    tenant_users = User.objects.filter(
        role='tenant'
    ).order_by('username')

    context = {
        'notifications': notifications,
        'tenant_users': tenant_users,
        'total_notifications': notifications.count(),
        'unread_notifications': notifications.filter(
            is_read=False
        ).count(),
        'read_notifications': notifications.filter(
            is_read=True
        ).count(),
    }

    return render(
        request,
        'notifications/admin_notifications.html',
        context
    )


@login_required
def send_notification(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method != 'POST':
        return redirect('admin_notifications')

    title = request.POST.get('title', '').strip()
    message = request.POST.get('message', '').strip()
    notification_type = request.POST.get(
        'notification_type',
        'general'
    )
    recipient = request.POST.get('recipient', '').strip()

    valid_types = ['rent', 'payment', 'general']

    if not title or not message:
        messages.error(
            request,
            'Please enter both a title and a message.'
        )
        return redirect('admin_notifications')

    if notification_type not in valid_types:
        messages.error(
            request,
            'Please select a valid notification type.'
        )
        return redirect('admin_notifications')

    if recipient == 'all':

        recipients = User.objects.filter(
            role='tenant'
        )

    else:

        try:
            tenant_id = int(recipient)

            tenant = get_object_or_404(
                User,
                id=tenant_id,
                role='tenant'
            )

            recipients = User.objects.filter(
                id=tenant.id
            )

        except (ValueError, TypeError):

            messages.error(
                request,
                'Please select a valid tenant.'
            )
            return redirect('admin_notifications')

    notification_records = [
        Notification(
            user=tenant_user,
            title=title,
            message=message,
            notification_type=notification_type
        )
        for tenant_user in recipients
    ]

    if not notification_records:
        messages.warning(
            request,
            'There are no tenant accounts to receive this notification.'
        )
        return redirect('admin_notifications')

    Notification.objects.bulk_create(
        notification_records
    )

    messages.success(
        request,
        f'Notification successfully sent to {len(notification_records)} tenant(s).'
    )

    return redirect('admin_notifications')
