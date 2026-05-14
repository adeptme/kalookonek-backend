from django.urls import path

from . import views

urlpatterns = [
    path('qr/patient/basic.html', views.qr_code_png_basic, name='qr_code_png_basic'),
    path('qr/patient/full.html', views.qr_code_png_full, name='qr_code_png_full'),
    path('qr/scan/basic/<str:token>/', views.qr_scan_basic, name='qr_scan_basic'),
    path('qr/scan/full/<str:token>/', views.qr_scan_full, name='qr_scan_full'),
]