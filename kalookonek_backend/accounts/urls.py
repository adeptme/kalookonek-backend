from django.urls import path

from . import views

urlpatterns = [
    path('accounts/login/', views.login, name='login'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/reset-password/', views.reset_password, name='reset_password'),
    path('accounts/settings/', views.account_settings, name='account_settings'),
]