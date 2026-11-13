
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Count
from django.db.models.deletion import ProtectedError

from .forms import PropertyForm
from .models import Property


# ==========================================================
# ADMIN ACCESS CHECK
# ==========================================================

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


# ==========================================================
# ADD PROPERTY
# ==========================================================

@login_required
def add_property(request):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    if request.method == 'POST':

        form = PropertyForm(request.POST)

        if form.is_valid():

            property_obj = form.save(commit=False)
            property_obj.owner = request.user
            property_obj.save()

            messages.success(
                request,
                'Property added successfully!'
            )

            return redirect('property_list')

    else:
        form = PropertyForm()

    return render(
        request,
        'properties/add_property.html',
        {
            'form': form
        }
    )


# ==========================================================
# PROPERTY LIST
# ==========================================================

@login_required
def property_list(request):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    properties = Property.objects.annotate(
        tenant_count=Count('tenants')
    ).select_related(
        'owner'
    ).order_by('-created_at')

    return render(
        request,
        'properties/property_list.html',
        {
            'properties': properties
        }
    )


# ==========================================================
# EDIT PROPERTY
# ==========================================================

@login_required
def edit_property(request, property_id):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    property_obj = get_object_or_404(
        Property,
        id=property_id
    )

    if request.method == 'POST':

        form = PropertyForm(
            request.POST,
            instance=property_obj
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Property details updated successfully!'
            )

            return redirect('property_list')

    else:

        form = PropertyForm(
            instance=property_obj
        )

    return render(
        request,
        'properties/edit_property.html',
        {
            'form': form,
            'property': property_obj
        }
    )


# ==========================================================
# DELETE PROPERTY
# ==========================================================

@login_required
def delete_property(request, property_id):

    if not is_admin(request.user):
        return HttpResponseForbidden(
            "Access denied. Administrators only."
        )

    property_obj = get_object_or_404(
        Property,
        id=property_id
    )

    if request.method == 'POST':

        try:

            property_obj.delete()

            messages.success(
                request,
                'Property deleted successfully!'
            )

        except ProtectedError:

            messages.error(
                request,
                'This property cannot be deleted because it has '
                'tenant records. Reassign or resolve those tenancies '
                'before deleting the property.'
            )

        return redirect('property_list')

    return render(
        request,
        'properties/delete_property.html',
        {
            'property': property_obj
        }
    )
