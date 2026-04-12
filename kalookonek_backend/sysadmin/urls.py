from django.urls import path

from . import views

urlpatterns = [
    path('admin/', views.dashboard, name='dashboard'),
    path('admin/update/', views.admin, name='admin'),
    path('admin/users/', views.all_users, name='all_users'),
    path('admin/users/<int:id>/', views.user, name='user'),
    path('admin/announcements/', views.announcements, name='announcements'),
    path('admin/announcements/<int:id>/', views.announcement, name='announcement'),
    path('admin/appointment-requests/', views.appointment_request, name='appointment_request'),
    path('admin/refill-requests/', views.refill_requests, name='refill_requests'),
]