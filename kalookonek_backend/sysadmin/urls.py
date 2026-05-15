from django.urls import path

from . import views

urlpatterns = [
    path('sysad/dashboard/', views.dashboard, name='admin_dashboard'),
    path('sysad/profile/', views.admin_profile, name='admin_profile'),
    path('sysad/users/', views.all_users, name='all_users'),
    path('sysad/users/create/', views.admin_create_account, name='admin_create_account'),
    path('sysad/users/<str:display_id>/', views.user_detail, name='user_detail'),
    path('sysad/announcements/', views.announcements, name='announcements'),
    path('sysad/announcements/<int:id>/', views.announcement_detail, name='announcement_detail'),
    path('sysad/appointment-requests/', views.appointment_requests, name='appointment_requests'),
    path('sysad/appointment-requests/<int:id>/', views.appointment_request_detail, name='appointment_request_detail'),
    path('sysad/refill-requests/', views.refill_requests, name='refill_requests'),
    path('sysad/refill-requests/<int:id>/', views.refill_request_detail, name='refill_request_detail'),
    path('sysad/logs/', views.admin_logs, name='system_logs'),
    # Registration request management
    path('sysad/registration-requests/', views.registration_requests, name='registration_requests'),
    path('sysad/registration-requests/<int:id>/approve/', views.registration_request_approve, name='registration_request_approve'),
    path('sysad/registration-requests/<int:id>/reject/', views.registration_request_reject, name='registration_request_reject'),
]