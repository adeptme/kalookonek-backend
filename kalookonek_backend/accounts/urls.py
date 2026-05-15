from django.urls import path
from . import views

urlpatterns = [
    path('accounts/login/', views.login_user, name='login'),
    # --- Registration & Access ---
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/request-access/', views.request_access, name='request_access'),

    # --- Profile & Dashboard ---
    path('accounts/profile/', views.get_profile, name='get_profile'),

    # --- Settings ---
    path('accounts/settings/details/',
         views.get_profile_details, name='get_profile_details'),
    path('accounts/settings/update/',
         views.update_profile_info, name='update_profile_info'),
    path('accounts/settings/change-password/',
         views.change_password, name='change_password'),
]
