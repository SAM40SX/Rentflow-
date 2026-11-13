
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import User, SystemSettings
from .forms import TenantProfileForm, TenantRegistrationForm

from properties.models import Property
from tenants.models import Tenant
from payments.models import Payment
from reminders.models import RentReminder
from notifications.models import Notification


# =====================================================
# LOGIN
# =====================================================

def login_view(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            if not user.is_active or not user.is_active_account:
                return render(
                    request,
                    'accounts/login.html',
                    {
                        'error': (
                            'Your account is awaiting approval or '
                            'has been deactivated. Contact the administrator.'
                        )
                    }
                )

            login(request, user)

            if user.role == 'admin':
                return redirect('admin_dashboard')

            return redirect('tenant_dashboard')

        return render(
            request,
            'accounts/login.html',
            {'error': 'Invalid username or password.'}
        )

    return render(request, 'accounts/login.html')


# =====================================================
# TENANT REGISTRATION
# =====================================================

def register_view(request):

    if request.user.is_authenticated:

        if request.user.role == 'admin':
            return redirect('admin_dashboard')

        return redirect('tenant_dashboard')

    if request.method == 'POST':

        form = TenantRegistrationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Your registration was successful! '
                'Your account is awaiting administrator approval. '
                'You will be able to log in after your property details '
                'have been assigned and your account activated.'
            )

            return redirect('login')

    else:
        form = TenantRegistrationForm()

    return render(
        request,
        'accounts/register.html',
        {'form': form}
    )


# =====================================================
# LOGOUT
# =====================================================

def logout_view(request):

    logout(request)

    return redirect('login')


# =====================================================
# ADMIN DASHBOARD
# =====================================================

@login_required
def admin_dashboard(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    today = timezone.localdate()

    total_properties = Property.objects.count()

    active_tenants = Tenant.objects.filter(
        is_active=True
    )

    total_tenants = active_tenants.count()

    monthly_collection = Payment.objects.filter(
        status='paid',
        payment_date__year=today.year,
        payment_date__month=today.month
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    tenants_with_payments = active_tenants.annotate(
        paid_this_month=Sum(
            'payments__amount',
            filter=Q(
                payments__status='paid',
                payments__payment_date__year=today.year,
                payments__payment_date__month=today.month
            )
        )
    )

    outstanding_rent = Decimal('0.00')

    for tenant in tenants_with_payments:

        paid = tenant.paid_this_month or Decimal('0.00')

        balance = tenant.monthly_rent - paid

        if balance > 0:
            outstanding_rent += balance

    recent_payments = Payment.objects.select_related(
        'tenant',
        'tenant__tenant_user',
        'tenant__property'
    ).order_by(
        '-payment_date',
        '-created_at'
    )[:5]

    upcoming_reminders = RentReminder.objects.select_related(
        'tenant',
        'tenant__tenant_user',
        'tenant__property'
    ).filter(
        reminder_type__in=['upcoming', 'due', 'overdue']
    ).order_by(
        'reminder_date',
        '-created_at'
    )[:5]

    context = {
        'total_properties': total_properties,
        'total_tenants': total_tenants,
        'monthly_collection': monthly_collection,
        'outstanding_rent': outstanding_rent,
        'recent_payments': recent_payments,
        'upcoming_reminders': upcoming_reminders,
    }

    return render(
        request,
        'admin/dashboard.html',
        context
    )


# =====================================================
# TENANT DASHBOARD
# =====================================================

@login_required
def tenant_dashboard(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    today = timezone.localdate()

    settings = SystemSettings.objects.filter(pk=1).first()

    rent_due_day = settings.rent_due_day if settings else 10

    tenant = getattr(
        request.user,
        'tenant_profile',
        None
    )

    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    monthly_rent = Decimal('0.00')
    payment_total = Decimal('0.00')

    next_payment = today.replace(day=rent_due_day)

    payment_status = 'Not set'

    recent_payments = []

    if tenant:

        monthly_rent = tenant.monthly_rent

        payment_total = tenant.payments.filter(
            payment_type='rent',
            status='paid',
            payment_date__year=today.year,
            payment_date__month=today.month
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
        if monthly_rent > 0 and payment_total >= monthly_rent:
            payment_status = 'Paid'

        elif payment_total > 0:
            payment_status = 'Partially Paid'

        else:
            payment_status = 'Pending'

        if today > next_payment:

            if today.month == 12:

                next_payment = today.replace(
                    year=today.year + 1,
                    month=1,
                    day=rent_due_day
                )

            else:

                next_payment = today.replace(
                    month=today.month + 1,
                    day=rent_due_day
                )

        recent_payments = tenant.payments.order_by(
            '-payment_date',
            '-created_at'
        )[:3]

    context = {
        'tenant_name': request.user.username,
        'monthly_rent': monthly_rent,
        'next_payment': next_payment,
        'rent_due_day': rent_due_day,
        'payment_status': payment_status,
        'unread_notifications': unread_notifications,
        'recent_payments': recent_payments,
    }

    return render(
        request,
        'tenants/dashboard.html',
        context
    )


# =====================================================
# TENANT MY PROPERTY
# =====================================================

@login_required
def tenant_my_property(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    tenant = getattr(
        request.user,
        'tenant_profile',
        None
    )

    context = {
        'tenant_name': request.user.username,
        'tenant': tenant,
    }

    return render(
        request,
        'tenants/my_property.html',
        context
    )


# =====================================================
# TENANT PROFILE
# =====================================================

@login_required
def tenant_profile(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    form = TenantProfileForm(
        request.POST or None,
        instance=request.user
    )

    if request.method == 'POST':

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Your profile has been updated successfully.'
            )

            return redirect('tenant_profile')

    profile_fields = [
        request.user.first_name,
        request.user.last_name,
        request.user.email,
        request.user.phone_number,
    ]

    completed_fields = sum(
        1 for field in profile_fields
        if field and field.strip()
    )

    profile_completion = int(
        (completed_fields / 4) * 100
    )

    context = {
        'form': form,
        'tenant_name': request.user.username,
        'profile_completion': profile_completion,
        'completed_fields': completed_fields,
        'total_fields': 4,
    }

    return render(
        request,
        'tenants/profile.html',
        context
    )


# =====================================================
# TENANT CHANGE PASSWORD
# =====================================================

@login_required
def tenant_change_password(request):

    if request.user.role != 'tenant':
        return HttpResponseForbidden(
            "Access denied. Tenants only."
        )

    if request.method == 'POST':

        form = PasswordChangeForm(
            user=request.user,
            data=request.POST
        )

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                'Your password has been changed successfully.'
            )

            return redirect('tenant_change_password')

    else:

        form = PasswordChangeForm(
            user=request.user
        )

    context = {
        'form': form,
        'tenant_name': request.user.username,
    }

    return render(
        request,
        'tenants/change_password.html',
        context
    )


# =====================================================
# USER MANAGEMENT - VIEW ALL USERS
# =====================================================

@login_required
def manage_users(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    users = User.objects.all().order_by('-created_at')

    pending_tenants = User.objects.filter(
        role='tenant',
        is_active=False,
        is_active_account=False,
        tenant_profile__isnull=True
    ).order_by('-created_at')

    properties = Property.objects.all().order_by('name')

    context = {
        'users': users,
        'pending_tenants': pending_tenants,
        'properties': properties,

        'admin_count': users.filter(
            role='admin'
        ).count(),

        'tenant_count': users.filter(
            role='tenant'
        ).count(),

        'active_count': users.filter(
            is_active=True,
            is_active_account=True
        ).count(),
    }

    return render(
        request,
        'accounts/manage_users.html',
        context
    )


# =====================================================
# APPROVE NEW TENANT
# =====================================================

@login_required
@require_POST
def approve_tenant(request, user_id):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    user = get_object_or_404(
        User,
        id=user_id,
        role='tenant'
    )

    if user.is_active or user.is_active_account:

        messages.error(
            request,
            'This tenant account is already active.'
        )

        return redirect('manage_users')

    if hasattr(user, 'tenant_profile'):

        messages.error(
            request,
            'This user already has a tenant profile.'
        )

        return redirect('manage_users')

    # Validate property
    property_id = request.POST.get('property')

    property_obj = get_object_or_404(
        Property,
        id=property_id
    )

    # Validate move-in date
    try:

        move_in_date = datetime.strptime(
            request.POST.get('move_in_date', ''),
            '%Y-%m-%d'
        ).date()

    except (ValueError, TypeError):

        messages.error(
            request,
            'Please enter a valid move-in date.'
        )

        return redirect('manage_users')

    # Validate monthly rent
    try:

        monthly_rent = Decimal(
            request.POST.get('monthly_rent', '')
        )

        if not monthly_rent.is_finite() or monthly_rent <= 0:
            raise InvalidOperation

    except (InvalidOperation, ValueError, TypeError):

        messages.error(
            request,
            'Monthly rent must be a valid amount greater than zero.'
        )

        return redirect('manage_users')

    # Validate deposit
    try:

        deposit_amount = Decimal(
            request.POST.get('deposit_amount') or '0'
        )

        if not deposit_amount.is_finite() or deposit_amount < 0:
            raise InvalidOperation

    except (InvalidOperation, ValueError, TypeError):

        messages.error(
            request,
            'Deposit must be a valid amount of zero or more.'
        )

        return redirect('manage_users')

    # Create tenant profile and activate account together
    try:

        with transaction.atomic():

            Tenant.objects.create(
                tenant_user=user,
                property=property_obj,
                move_in_date=move_in_date,
                monthly_rent=monthly_rent,
                deposit_amount=deposit_amount,
                is_active=True
            )

            user.is_active = True
            user.is_active_account = True

            user.save(
                update_fields=[
                    'is_active',
                    'is_active_account',
                    'updated_at'
                ]
            )

    except Exception:

        messages.error(
            request,
            'The tenant could not be approved. Please check the details and try again.'
        )

        return redirect('manage_users')

    messages.success(
        request,
        f'{user.username} has been approved and their tenant profile created.'
    )

    return redirect('manage_users')


# =====================================================
# USER MANAGEMENT - ACTIVATE / DEACTIVATE ACCOUNT
# =====================================================

@login_required
@require_POST
def toggle_user_status(request, user_id):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    user = get_object_or_404(
        User,
        id=user_id
    )

    if user.id == request.user.id:

        messages.error(
            request,
            "You cannot deactivate your own account."
        )

        return redirect('manage_users')

    if user.is_superuser:

        messages.error(
            request,
            "Superuser accounts cannot be deactivated here."
        )

        return redirect('manage_users')

    # Prevent bypassing the tenant approval process
    if (
        user.role == 'tenant'
        and not user.is_active
        and not hasattr(user, 'tenant_profile')
    ):

        messages.error(
            request,
            "Approve this tenant and assign their property details before activating the account."
        )

        return redirect('manage_users')

    if user.role == 'admin' and user.is_active:

        active_admins = User.objects.filter(
            role='admin',
            is_active=True
        ).count()

        if active_admins <= 1:

            messages.error(
                request,
                "You cannot deactivate the last active administrator."
            )

            return redirect('manage_users')

    user.is_active = not user.is_active
    user.is_active_account = user.is_active

    user.save(
        update_fields=[
            'is_active',
            'is_active_account',
            'updated_at'
        ]
    )

    if user.is_active:

        messages.success(
            request,
            f"{user.username}'s account has been activated."
        )

    else:

        messages.success(
            request,
            f"{user.username}'s account has been deactivated."
        )

    return redirect('manage_users')


# =====================================================
# USER MANAGEMENT - CHANGE USER ROLE
# =====================================================

@login_required
@require_POST
def change_user_role(request, user_id):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    user = get_object_or_404(
        User,
        id=user_id
    )

    new_role = request.POST.get('role')

    if user.id == request.user.id:

        messages.error(
            request,
            "You cannot change your own administrator role."
        )

        return redirect('manage_users')

    if user.is_superuser:

        messages.error(
            request,
            "Superuser roles cannot be changed here."
        )

        return redirect('manage_users')

    allowed_roles = [
        choice[0]
        for choice in User.ROLE_CHOICES
    ]

    if new_role not in allowed_roles:

        messages.error(
            request,
            "Invalid user role selected."
        )

        return redirect('manage_users')

    if (
        user.role == 'admin'
        and new_role != 'admin'
        and user.is_active
    ):

        active_admins = User.objects.filter(
            role='admin',
            is_active=True
        ).count()

        if active_admins <= 1:

            messages.error(
                request,
                "You cannot remove the role of the last active administrator."
            )

            return redirect('manage_users')

    user.role = new_role

    user.save(
        update_fields=[
            'role',
            'updated_at'
        ]
    )

    messages.success(
        request,
        f"{user.username}'s role has been updated successfully."
    )

    return redirect('manage_users')


# =====================================================
# SYSTEM SETTINGS
# =====================================================

@login_required
def system_settings(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    settings, created = SystemSettings.objects.get_or_create(
        pk=1
    )

    if request.method == 'POST':

        settings.system_name = request.POST.get(
            'system_name', 'RentFlow'
        )

        settings.company_name = request.POST.get(
            'company_name', ''
        )

        settings.contact_email = request.POST.get(
            'contact_email', ''
        )

        settings.contact_phone = request.POST.get(
            'contact_phone', ''
        )

        settings.address = request.POST.get(
            'address', ''
        )

        settings.currency = request.POST.get(
            'currency', 'KES'
        )

        try:

            due_day = int(
                request.POST.get('rent_due_day', 10)
            )

            if not 1 <= due_day <= 28:
                raise ValueError

            settings.rent_due_day = due_day

        except (ValueError, TypeError):

            messages.error(
                request,
                'Rent due day must be between 1 and 28.'
            )

            return redirect('system_settings')

        settings.email_notifications = (
            request.POST.get('email_notifications') == 'on'
        )

        settings.sms_notifications = (
            request.POST.get('sms_notifications') == 'on'
        )

        settings.save()

        messages.success(
            request,
            'System settings updated successfully.'
        )

        return redirect('system_settings')

    return render(
        request,
        'accounts/system_settings.html',
        {'settings': settings}
    )
