
from django.urls import path
from . import views


urlpatterns = [
    # Tenant Registration
    path(
        'register/',
        views.register_tenant,
        name='register_tenant'
    ),

    # Tenant Management
    path(
        'list/',
        views.tenant_list,
        name='tenant_list'
    ),

    path(
        'edit/<int:tenant_id>/',
        views.edit_tenant,
        name='edit_tenant'
    ),

    path(
        'delete/<int:tenant_id>/',
        views.delete_tenant,
        name='delete_tenant'
    ),

    # Property Assignment
    path(
        'assign/',
        views.assign_tenant,
        name='assign_tenant'
    ),

    path(
        'assigned/',
        views.assigned_tenant_list,
        name='assigned_tenant_list'
    ),
]
