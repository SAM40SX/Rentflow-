
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [

    # =================================================
    # AUTHENTICATION
    # =================================================

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Tenant registration
    path('register/', views.register_view, name='register'),

    # =================================================
    # FORGOT PASSWORD AND PASSWORD RESET
    # =================================================

    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='/password-reset/done/'
        ),
        name='password_reset'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/reset/complete/'
        ),
        name='password_reset_confirm'
    ),

    path(
        'reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    # =================================================
    # ADMIN DASHBOARD
    # =================================================

    path(
        'dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

    # =================================================
    # USER MANAGEMENT
    # =================================================

    path(
        'users/',
        views.manage_users,
        name='manage_users'
    ),

    # Approve new tenant and assign property details
    path(
        'users/approve-tenant/<int:user_id>/',
        views.approve_tenant,
        name='approve_tenant'
    ),

    # Activate / deactivate users
    path(
        'users/toggle-status/<int:user_id>/',
        views.toggle_user_status,
        name='toggle_user_status'
    ),

    # Change user role
    path(
        'users/change-role/<int:user_id>/',
        views.change_user_role,
        name='change_user_role'
    ),

    # =================================================
    # SYSTEM SETTINGS
    # =================================================

    path(
        'settings/',
        views.system_settings,
        name='system_settings'
    ),

    # =================================================
    # TENANT DASHBOARD
    # =================================================

    path(
        'tenant-dashboard/',
        views.tenant_dashboard,
        name='tenant_dashboard'
    ),

    # Tenant property
    path(
        'tenant/my-property/',
        views.tenant_my_property,
        name='tenant_my_property'
    ),

    # Tenant profile
    path(
        'tenant/profile/',
        views.tenant_profile,
        name='tenant_profile'
    ),

    # Tenant password
    path(
        'tenant/change-password/',
        views.tenant_change_password,
        name='tenant_change_password'
    ),

]
