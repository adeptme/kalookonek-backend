from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='user_dashboard'),
    path('user/', views.user_profile, name='user_profile'),
    path('health-record/', views.health_record, name='health_record'),
    path('qr-code/', views.qr_code, name='qr_code'),
    path('emergency-contacts/', views.emergency_contacts, name='emergency_contacts'),
    path('medicine/', views.medicine, name='medicine'),
    path('appointments/', views.appointments, name='appointments'),
]