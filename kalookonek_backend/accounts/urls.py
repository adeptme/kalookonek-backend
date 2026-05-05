from django.urls import path
from . import views

urlpatterns = [

    path('login/', views.login, name='login'),
    path('profile/', views.get_profile, name='get_profile'),
    path('directory/', views.get_all_patients, name='patient_directory'),
    path('patients/', views.get_recent_patients, name='recent_patients'),
    path('settings/', views.account_settings, name='account_settings'),
    path('appointments/', views.get_appointments, name='get_appointments'),
]
