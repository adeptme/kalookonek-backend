from django.contrib import admin
from .models import PatientProfile, MedicalRecord


class MedicalRecordInline(admin.TabularInline):
    model = MedicalRecord
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'sex', 'blood_type', 'barangay')
    list_filter = ('sex', 'blood_type', 'barangay')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'barangay')
    inlines = [MedicalRecordInline]


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'attending_staff', 'visit_date', 'diagnosis', 'follow_up_date')
    list_filter = ('visit_date', 'attending_staff')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'diagnosis')
    date_hierarchy = 'visit_date'