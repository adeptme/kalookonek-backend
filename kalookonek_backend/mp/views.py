import json
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from kalookonek_backend.accounts.auth import role_required
from kalookonek_backend.mp.models import PatientProfile, MedicalRecord

# DRF Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@role_required('staff', 'admin')
def dashboard(request):
    """GET — staff dashboard with patient count and recent records."""
    if request.method == 'GET':
        total_patients = PatientProfile.objects.count()
        recent_records = MedicalRecord.objects.select_related('patient__user').order_by('-created_at')[:5]
        recent_list = [{
            "id": str(r.id),
            "name": r.patient.user.get_full_name(),
            "purpose": r.diagnosis or "General Checkup",
            "status": r.status,
            "visit_date": r.visit_date.isoformat(),
        } for r in recent_records]
        return JsonResponse({"total_patients": total_patients, "recent_records": recent_list})
    return JsonResponse({"error": "Method not allowed."}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointments(request):
    """Returns a list of scheduled medical records (appointments)."""
    status = request.query_params.get('status', 'SCHEDULED')
    records = MedicalRecord.objects.filter(status=status).select_related('patient__user').order_by('visit_date', 'appointment_time')
    data = [{
        'id': mr.id,
        'patient_name': mr.patient.user.get_full_name(),
        'patient_id_display': mr.patient.user.profile.display_id,
        'time': mr.appointment_time.strftime('%I:%M %p') if mr.appointment_time else "TBA",
        'status': mr.status,
    } for mr in records]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointment_detail(request, record_id):
    """Returns detailed info for a specific medical record."""
    mr = get_object_or_404(MedicalRecord, id=record_id)
    return Response({
        'id': mr.id,
        'patient_name': mr.patient.user.get_full_name(),
        'patient_id_display': mr.patient.user.profile.display_id,
        'status': mr.status,
        'dob': mr.patient.date_of_birth,
        'age': mr.patient.age,
        'blood_pressure': mr.blood_pressure,
        'temperature': mr.temperature,
        'weight': mr.weight,
        'diagnosis': mr.diagnosis,
        'treatment': mr.treatment,
        'prescription': mr.prescription,
        'notes': mr.notes,
        'visit_date': mr.visit_date,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_consultation(request, record_id):
    """Updates a medical record with consultation findings."""
    mr = get_object_or_404(MedicalRecord, id=record_id)
    data = request.data
    try:
        mr.blood_pressure = data.get('blood_pressure', mr.blood_pressure)
        mr.temperature = data.get('temperature', mr.temperature)
        mr.weight = data.get('weight', mr.weight)
        mr.diagnosis = data.get('diagnosis', mr.diagnosis)
        mr.treatment = data.get('treatment', mr.treatment)
        mr.prescription = data.get('prescription', mr.prescription)
        mr.notes = data.get('notes', mr.notes)
        mr.status = 'COMPLETED'
        mr.attending_staff = request.user
        mr.save()
        return Response({'message': 'Consultation saved successfully.'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_patient(request):
    """Returns the next scheduled patient for today."""
    today = timezone.now().date()
    current_visit = MedicalRecord.objects.filter(visit_date=today, status='SCHEDULED').order_by('appointment_time').first()
    if not current_visit:
        return Response({"message": "No active patient scheduled for today"}, status=404)
    return Response({
        'id': current_visit.id,
        'patient_name': current_visit.patient.user.get_full_name(),
        'display_id': current_visit.patient.user.profile.display_id,
        'age': current_visit.patient.age,
    })

# ... (Keeping existing directory and search views) ...
@role_required('staff', 'admin')
def patient_directory(request):
    if request.method == 'GET':
        patients = PatientProfile.objects.select_related('user', 'user__profile').all()
        patient_list = [{
            'id': p.id,
            'name': p.user.get_full_name(),
            'age': p.age,
            'brgy': p.barangay,
        } for p in patients]
        return JsonResponse({"patients": patient_list})
    return JsonResponse({"error": "Method not allowed."}, status=405)