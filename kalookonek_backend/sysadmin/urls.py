from django.urls import path

from . import views

urlpatterns = [
    path('admin/dashboard/', views.dashboard, name='admin_dashboard'),
    path('admin/profile/', views.admin_profile, name='admin_profile'),
    path('admin/users/', views.all_users, name='all_users'),
    path('admin/users/<str:display_id>/', views.user_detail, name='user_detail'),
    path('admin/announcements/', views.announcements, name='announcements'),
    path('admin/announcements/<int:id>/', views.announcement_detail, name='announcement_detail'),
    path('admin/appointment-requests/', views.appointment_requests, name='appointment_requests'),
    path('admin/appointment-requests/<int:id>/', views.appointment_request_detail, name='appointment_request_detail'),
    path('admin/refill-requests/', views.refill_requests, name='refill_requests'),
    path('admin/refill-requests/<int:id>/', views.refill_request_detail, name='refill_request_detail'),
    path('admin/registration-requests/', views.registration_requests, name='registration_requests'),
    path('admin/registration-requests/<int:id>/approve/', views.registration_request_approve, name='registration_request_approve'),
    path('admin/registration-requests/<int:id>/reject/', views.registration_request_reject, name='registration_request_reject'),
]