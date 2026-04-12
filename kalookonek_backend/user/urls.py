from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('user/', views.user, name='user'),
    path('health-record/', views.health_record, name='health_record'),
    path('qr-code/', views.qr_code, name='qr_code'),
    path('emergency-contacts/', views.emergency_contacts, name='emergency_contacts'),
    path('medicine/', views.medicine, name='medicine'),
    path('appointments/', views.appointments, name='appointments'),
]