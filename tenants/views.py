
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import IntegrityError, transaction

from .forms import TenantRegistrationForm, TenantAssignmentForm
from .models import Tenant

User = get_user_model()


# ==========================================================
# ADMIN ACCESS CHECK
# ==========================================================

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


# ==========================================================
# PHONE NUMBER VALIDATION
# ==========================================================

def valid_phone_number(phone):
    import re

    phone = (phone or '').strip()

    if not re.fullmatch(r'\+?[0-9]+', phone):
        return False

    digits = phone.lstrip('+')

    return 9 <= len(digits) <= 15


# ==========================================================
# REGISTER TENANT
# ==========================================================

@login_required
def register_tenant(request):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method == 'POST':

        form = TenantRegistrationForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data['email'].strip()
            phone_number = form.cleaned_data['phone_number'].strip()

            if User.objects.filter(
                email__iexact=email
            ).exists():

                form.add_error(
                    'email',
                    'An account with this email already exists.'
                )

            elif not valid_phone_number(phone_number):

                form.add_error(
                    'phone_number',
                    'Enter a valid phone number using digits only.'
                )

            else:

                try:
                    User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=email,
                        password=form.cleaned_data['password'],
                        phone_number=phone_number,
                        role='tenant',
                        is_active=True,
                        is_active_account=True
                    )

                    messages.success(
                        request,
                        'Tenant account created successfully. '
                        'You can now assign the tenant to a property.'
                    )

                    return redirect('tenant_list')

                except IntegrityError:
                    form.add_error(
                        'username',
                        'This username is already taken.'
                    )

    else:
        form = TenantRegistrationForm()

    return render(
        request,
        'tenants/register.html',
        {'form': form}
    )


# ==========================================================
# TENANT LIST
# ==========================================================

@login_required
def tenant_list(request):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    tenants = User.objects.filter(
        role='tenant'
    ).select_related(
        'tenant_profile',
        'tenant_profile__property'
    ).order_by('-date_joined')

    return render(
        request,
        'tenants/tenant_list.html',
        {
            'tenants': tenants
        }
    )


# ==========================================================
# EDIT TENANT
# ==========================================================

@login_required
def edit_tenant(request, tenant_id):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    tenant = get_object_or_404(
        User,
        id=tenant_id,
        role='tenant'
    )

    if request.method == 'POST':

        username = request.POST.get(
            'username', ''
        ).strip()

        email = request.POST.get(
            'email', ''
        ).strip()

        phone_number = request.POST.get(
            'phone_number', ''
        ).strip()

        is_active = (
            request.POST.get('is_active_account') == 'on'
        )

        if not username:

            messages.error(
                request,
                'Username is required.'
            )

        elif User.objects.filter(
            username__iexact=username
        ).exclude(id=tenant.id).exists():

            messages.error(
                request,
                'This username is already in use.'
            )

        elif email and User.objects.filter(
            email__iexact=email
        ).exclude(id=tenant.id).exists():

            messages.error(
                request,
                'This email address is already registered.'
            )

        elif not valid_phone_number(phone_number):

            messages.error(
                request,
                'Enter a valid phone number using digits only.'
            )

        else:

            tenant.username = username
            tenant.email = email
            tenant.phone_number = phone_number

            # Keep both account status fields synchronized.
            tenant.is_active = is_active
            tenant.is_active_account = is_active

            tenant.save()

            messages.success(
                request,
                'Tenant information updated successfully.'
            )

            return redirect('tenant_list')

    return render(
        request,
        'tenants/edit_tenant.html',
        {
            'tenant': tenant
        }
    )


# ==========================================================
# DEACTIVATE TENANT
# ==========================================================

@login_required
def delete_tenant(request, tenant_id):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    tenant = get_object_or_404(
        User,
        id=tenant_id,
        role='tenant'
    )

    if request.user.id == tenant.id:

        messages.error(
            request,
            'You cannot deactivate your own account.'
        )

        return redirect('tenant_list')

    if request.method == 'POST':

        tenant.is_active = False
        tenant.is_active_account = False
        tenant.save()

        messages.success(
            request,
            'Tenant account deactivated successfully.'
        )

        return redirect('tenant_list')

    return render(
        request,
        'tenants/delete_tenant.html',
        {
            'tenant': tenant
        }
    )


# ==========================================================
# ASSIGN TENANT TO PROPERTY
# ==========================================================

@login_required
def assign_tenant(request):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method == 'POST':

        form = TenantAssignmentForm(request.POST)

        if form.is_valid():

            selected_tenant = form.cleaned_data['tenant_user']

            if not selected_tenant.is_active or not selected_tenant.is_active_account:

                form.add_error(
                    'tenant_user',
                    'This tenant account is inactive.'
                )

            elif Tenant.objects.filter(
                tenant_user=selected_tenant
            ).exists():

                form.add_error(
                    'tenant_user',
                    'This tenant is already assigned to a property.'
                )

            else:

                try:
                    with transaction.atomic():

                        assignment = form.save(commit=False)
                        assignment.is_active = True
                        assignment.save()

                    messages.success(
                        request,
                        'Tenant assigned to property successfully.'
                    )

                    return redirect('assigned_tenant_list')

                except IntegrityError:

                    form.add_error(
                        'tenant_user',
                        'This tenant already has a property assignment.'
                    )

    else:
        form = TenantAssignmentForm()

    return render(
        request,
        'tenants/assign_tenant.html',
        {
            'form': form
        }
    )


# ==========================================================
# ASSIGNED TENANT LIST
# ==========================================================

@login_required
def assigned_tenant_list(request):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    assignments = Tenant.objects.select_related(
        'tenant_user',
        'property'
    ).filter(
        is_active=True
    ).order_by('-created_at')

    return render(
        request,
        'tenants/assigned_tenant_list.html',
        {
            'assignments': assignments
        }
    )
