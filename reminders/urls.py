
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reminder_list, name='reminder_list'),
    path('generate/', views.generate_reminders, name='generate_reminders'),
]
