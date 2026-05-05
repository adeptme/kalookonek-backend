from django.contrib import admin
from .models import UserProfile, Appointment


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'start_time', 'end_time', 'status')
    list_filter = ('status',)
    search_fields = ('patient_name', 'patient_id_display')
