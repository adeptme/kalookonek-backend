from django.urls import path

from . import views

urlpatterns = [
    # Commented out: login, signup, and password reset are handled client-side via Supabase Auth
    # path('accounts/login/', views.login, name='login'),
    # path('accounts/create/', views.create_account, name='create_account'),
    # path('accounts/reset-password/', views.reset_password, name='reset_password'),

    # Active endpoints
    path('accounts/profile/', views.get_profile, name='get_profile'),
    path('accounts/settings/', views.account_settings, name='account_settings'),
]