from django.urls import path

from . import views

urlpatterns = [
    # Patient signup (replaces direct supabase.auth.signUp)
    path('accounts/create/', views.create_account, name='create_account'),

    # Staff/Admin access request (no password, awaits admin approval)
    path('accounts/request-access/', views.request_access, name='request_access'),

    # Authenticated user endpoints
    path('accounts/profile/', views.get_profile, name='get_profile'),
    path('accounts/settings/', views.account_settings, name='account_settings'),
]