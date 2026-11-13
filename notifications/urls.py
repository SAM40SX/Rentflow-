
from django.urls import path
from . import views

urlpatterns = [

    # Tenant notifications
    path(
        '',
        views.notification_list,
        name='notification_list'
    ),

    path(
        'mark-read/<int:notification_id>/',
        views.mark_notification_read,
        name='mark_notification_read'
    ),

    path(
        'mark-all-read/',
        views.mark_all_notifications_read,
        name='mark_all_notifications_read'
    ),

    # Admin notification management
    path(
        'admin/',
        views.admin_notifications,
        name='admin_notifications'
    ),

    path(
        'admin/send/',
        views.send_notification,
        name='send_notification'
    ),

]
