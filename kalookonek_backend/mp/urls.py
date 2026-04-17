from django.urls import path

from . import views

urlpatterns = [
    path('mp/dashboard/', views.dashboard, name='mp_dashboard'),
    path('mp/profile/', views.mp_profile, name='mp_profile'),
    path('mp/patients/', views.patient_directory, name='patient_directory'),
    path('mp/patients/search/', views.search_patient_by_name, name='search_patient_by_name'),
    path('mp/patients/filter/', views.search_filter_barangay, name='search_filter_barangay'),
    path('mp/patients/<int:patient_id>/record/', views.patient_record, name='patient_record'),
    path('mp/schedule/', views.schedule, name='mp_schedule'),
    path('mp/schedule/history/', views.schedule_history, name='mp_schedule_history'),
]