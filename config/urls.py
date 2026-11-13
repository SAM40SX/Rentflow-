from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),

    path('', include('accounts.urls')),

    path('tenants/', include('tenants.urls')),

    path('properties/', include('properties.urls')),

    path('payments/', include('payments.urls')),
    path('reminders/', include('reminders.urls')),
    path('notifications/', include('notifications.urls')),
    path('reports/', include('reports.urls')),
]