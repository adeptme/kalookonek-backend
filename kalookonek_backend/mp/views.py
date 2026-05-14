import json
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from kalookonek_backend.accounts.auth import role_required
from kalookonek_backend.mp.models import PatientProfile, MedicalRecord
from django.db.models import Q
from django.db.models import Q, Value
from django.db.models.functions import Concat

# DRF Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """GET — staff dashboard with patient count and recent records."""

    # 1. Manual Role Check (Replacing the @role_required decorator)
    # This ensures only staff/admin can see the data even if they have a valid token
    try:
        if request.user.userprofile.role not in ['staff', 'admin']:
            return Response({"error": "Forbidden: Staff access only."}, status=403)
    except Exception:
        return Response({"error": "User profile not found."}, status=403)

    # 2. Logic
    total_patients = PatientProfile.objects.count()
    recent_records = MedicalRecord.objects.select_related(
        'patient__user'
    ).order_by('-created_at')[:5]

    recent_list = [{
        "id": str(r.id),
        "name": r.patient.user.get_full_name(),
        "purpose": r.diagnosis or "General Checkup",
        "status": r.status,
        "visit_date": r.visit_date.isoformat() if r.visit_date else None,
    } for r in recent_records]

    # 3. Use DRF Response (instead of JsonResponse)
    return Response({
        "total_patients": total_patients,
        "recent_records": recent_list
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manual_lookup(request):
    query = request.query_params.get('query', '')
    if not query:
        return Response({"error": "Query parameter is required."}, status=400)

    try:
        patients = PatientProfile.objects.select_related(
            'user', 'user__profile'
        ).annotate(
            full_name=Concat('user__first_name', Value(' '), 'user__last_name')
        ).filter(
            Q(user__profile__display_id__iexact=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(full_name__icontains=query)
        )[:10]  # limit to 10 results
    except Exception as e:
        return Response({"error": "An error occurred while searching."}, status=500)

    if not patients:
        return Response({"error": "Patient not found."}, status=404)

    return Response([{
        "id": str(p.id),
        "name": p.user.get_full_name(),
        "display_id": p.user.profile.display_id,
        "blood_type": getattr(p, 'blood_type', None),
        "age": p.user.profile.calculated_age if hasattr(p.user, 'profile') else None,
        "sex": getattr(p, 'sex', None),
        "barangay": getattr(p, 'barangay', None),
        "emergency_contact_name": getattr(p, 'emergency_contact_name', None),
        "emergency_contact_number": getattr(p, 'emergency_contact_number', None),
        "allergies": getattr(p, 'allergies', None),
    } for p in patients])


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_patient_info(request, patient_id):
    """PUT — update patient info (for staff/admin)."""
    try:
        patient = PatientProfile.objects.select_related(
            'user').get(id=patient_id)
    except PatientProfile.DoesNotExist:
        return Response({"error": "Patient not found."}, status=404)

    data = request.data
    allowed_fields = ['address', 'barangay', 'emergency_contact_name',
                      'emergency_contact_number', 'allergies']

    for field in allowed_fields:
        if field in data:
            setattr(patient, field, data[field])

    try:
        patient.save()
        return Response({"message": "Patient information updated successfully."})
    except Exception as e:
        return Response({"error": "An error occurred while updating patient information."}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # This ensures the Token is checked
def get_appointments(request):
    """Returns a list of scheduled medical records (appointments)."""
    # 1. Get the tab from the Frontend (Dashboard.tsx/Appointments.tsx)
    tab = request.query_params.get('tab', "Today's List")
    today = timezone.now().date()

    # 2. Filter logic based on the Tab
    query = MedicalRecord.objects.select_related(
        'patient__user', 'patient__user__profile')

    if tab == "Today's List":
        records = query.filter(visit_date=today, status='SCHEDULED')
    elif tab == "Upcoming":
        records = query.filter(visit_date__gt=today, status='SCHEDULED')
    elif tab == "Past Records":
        records = query.filter(status='COMPLETED')
    else:
        records = query.filter(status='SCHEDULED')

    records = records.order_by('appointment_time')

    # 3. Format data to match your React Interfaces
    data = [{
        'id': mr.id,
        'patient_name': mr.patient.user.get_full_name(),
        'display_id': mr.patient.user.profile.display_id if hasattr(mr.patient.user.profile, 'display_id') else "N/A",
        'time': mr.appointment_time.strftime('%I:%M %p') if mr.appointment_time else "TBA",
        # Use a real field for purpose if you have one, or diagnosis
        'purpose': mr.diagnosis[:30] + "..." if mr.diagnosis else "Medical Consultation",
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
        'height': mr.height,
        'heart_rate': mr.heart_rate,
        'respiratory_rate': mr.respiratory_rate,
        'spo2': mr.spo2,
        'diagnosis': mr.diagnosis,
        'treatment': mr.treatment,
        'prescription': mr.prescription,
        'notes': mr.notes,
        'visit_date': mr.visit_date,

        # PATIENT PROFILE
        'patient_name': mr.patient.user.get_full_name(),
        'patient_id_display': mr.patient.user.profile.display_id,
        'dob': mr.patient.date_of_birth,
        'age': mr.patient.age,
        'sex': mr.patient.sex,
        'blood_type': mr.patient.blood_type,
        'allergies': mr.patient.allergies,
        'barangay': mr.patient.barangay,
        'emergency_contact_name': mr.patient.emergency_contact_name,
        'emergency_contact_number': mr.patient.emergency_contact_number,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_consultation(request, record_id):
    mr = get_object_or_404(MedicalRecord, id=record_id)
    data = request.data
    try:
        mr.blood_pressure = data.get('blood_pressure', mr.blood_pressure)
        mr.temperature = data.get('temperature', mr.temperature)
        mr.weight = data.get('weight', mr.weight)
        mr.height = data.get('height', mr.height)
        mr.heart_rate = data.get('heart_rate', mr.heart_rate)
        mr.respiratory_rate = data.get('respiratory_rate', mr.respiratory_rate)
        mr.spo2 = data.get('spo2', mr.spo2)
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
    current_visit = MedicalRecord.objects.filter(
        visit_date=today, status='SCHEDULED').order_by('appointment_time').first()
    if not current_visit:
        return Response({"message": "No active patient scheduled for today"}, status=404)
    return Response({
        'id': current_visit.id,
        'patient_name': current_visit.patient.user.get_full_name(),
        'display_id': current_visit.patient.user.profile.display_id,
        'age': current_visit.patient.age,
    })

# ... (Keeping existing directory and search views) ...


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_directory(request):
    search = request.query_params.get('search', '')
    barangay = request.query_params.get('barangay', '')

    patients = PatientProfile.objects.select_related(
        'user', 'user__profile').all()

    if search:
        patients = patients.filter(user__first_name__icontains=search) | \
            patients.filter(user__last_name__icontains=search)
    if barangay:
        patients = patients.filter(barangay__icontains=barangay)

    patient_list = [{
        'id': p.id,
        'display_id': p.user.profile.display_id if hasattr(p.user, 'profile') else 'N/A',
        'first_name': p.user.first_name,
        'last_name': p.user.last_name,
        'age': p.age,
        'gender': p.gender if hasattr(p, 'gender') else 'N/A',
        'barangay': p.barangay,
        'last_visit': p.medical_records.order_by('-visit_date').first().visit_date.isoformat()
        if p.medical_records.exists() else None,
    } for p in patients]

    return Response(patient_list)
