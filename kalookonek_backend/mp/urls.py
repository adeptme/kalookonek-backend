from django.urls import path
from . import views

urlpatterns = [
    # --- Dashboard ---
    path('mp/dashboard/', views.dashboard, name='dashboard'),

    # --- Appointments & Consultations ---
    path('mp/appointments/', views.get_appointments, name='get_appointments'),
    path('mp/appointments/<int:record_id>/',
         views.get_appointment_detail, name='get_appointment_detail'),
    path('mp/appointments/<int:record_id>/save/',
         views.save_consultation, name='save_consultation'),
    path('mp/appointments/current/', views.get_current_patient,
         name='get_current_patient'),

    # --- Directory & Search ---
    path('mp/directory/', views.patient_directory, name='patient_directory'),
]
