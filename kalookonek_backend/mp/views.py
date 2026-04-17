import json
from django.http import JsonResponse
from django.utils import timezone
from kalookonek_backend.accounts.auth import role_required
from kalookonek_backend.mp.models import PatientProfile, MedicalRecord


@role_required('staff', 'admin')
def dashboard(request):
    """GET — staff dashboard with patient count and recent records."""
    if request.method == 'GET':
        total_patients = PatientProfile.objects.count()
        recent_records = MedicalRecord.objects.select_related('patient__user').order_by('-created_at')[:5]

        recent_list = [
            {
                "id": str(r.id),
                "name": r.patient.user.get_full_name(),
                "purpose": r.diagnosis or "General Checkup",
                "status": r.status,
                "visit_date": r.visit_date.isoformat(),
            }
            for r in recent_records
        ]

        return JsonResponse({
            "total_patients": total_patients,
            "recent_records": recent_list
        })

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def mp_profile(request):
    """GET/PUT — staff member's own profile."""
    profile = request.user_profile
    user = request.user

    if request.method == 'GET':
        return JsonResponse({
            "display_id": profile.display_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": profile.role,
            "phone_number": profile.phone_number,
        })

    elif request.method == 'PUT':
        data = json.loads(request.body)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        profile.phone_number = data.get('phone_number', profile.phone_number)

        user.save()
        profile.save()

        return JsonResponse({"message": "Profile updated successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def patient_directory(request):
    """GET — list all patients."""
    if request.method == 'GET':
        patients = PatientProfile.objects.select_related('user', 'user__profile').all()

        patient_list = [
            {
                'id': p.id,
                'display_id': p.user.profile.display_id if hasattr(p.user, 'profile') else None,
                'name': p.user.get_full_name(),
                'age': p.age,
                'date_of_birth': p.date_of_birth.isoformat(),
                'gender': p.sex.capitalize(),
                'brgy': p.barangay,
            }
            for p in patients
        ]

        return JsonResponse({"patients": patient_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def search_patient_by_name(request):
    """GET — search patients by first or last name."""
    if request.method == 'GET':
        name = request.GET.get('name', '')
        patients = PatientProfile.objects.select_related('user', 'user__profile').filter(
            user__first_name__icontains=name
        ) | PatientProfile.objects.select_related('user', 'user__profile').filter(
            user__last_name__icontains=name
        )

        patient_list = [
            {
                'id': p.id,
                'display_id': p.user.profile.display_id if hasattr(p.user, 'profile') else None,
                'name': p.user.get_full_name(),
                'age': p.age,
                'date_of_birth': p.date_of_birth.isoformat(),
                'gender': p.sex.capitalize(),
                'brgy': p.barangay,
            }
            for p in patients
        ]

        return JsonResponse({"patients": patient_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def search_filter_barangay(request):
    """GET — filter patients by barangay."""
    if request.method == 'GET':
        barangay = request.GET.get('barangay', '')
        patients = PatientProfile.objects.select_related('user', 'user__profile').filter(
            barangay__icontains=barangay
        )

        patient_list = [
            {
                'id': p.id,
                'display_id': p.user.profile.display_id if hasattr(p.user, 'profile') else None,
                'name': p.user.get_full_name(),
                'age': p.age,
                'date_of_birth': p.date_of_birth.isoformat(),
                'gender': p.sex.capitalize(),
                'brgy': p.barangay,
            }
            for p in patients
        ]

        return JsonResponse({"patients": patient_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def patient_record(request, patient_id):
    """
    GET — return patient info + medical records.
    PUT — add a new medical record for this patient.
    """
    try:
        patient = PatientProfile.objects.select_related('user').get(id=patient_id)
    except PatientProfile.DoesNotExist:
        return JsonResponse({"error": "Patient not found."}, status=404)

    if request.method == 'GET':
        records = MedicalRecord.objects.filter(patient=patient).order_by('-visit_date')

        record_list = [
            {
                'id': r.id,
                'visit_date': r.visit_date.isoformat(),
                'diagnosis': r.diagnosis,
                'treatment': r.treatment,
                'prescription': r.prescription,
                'notes': r.notes,
                'blood_pressure': r.blood_pressure,
                'temperature': str(r.temperature) if r.temperature else None,
                'weight': str(r.weight) if r.weight else None,
                'status': r.status,
                'follow_up_date': r.follow_up_date.isoformat() if r.follow_up_date else None,
            }
            for r in records
        ]
        return JsonResponse({
            'patient': {
                'id': patient.id,
                'display_id': patient.user.profile.display_id if hasattr(patient.user, 'profile') else None,
                'name': patient.user.get_full_name(),
                'age': patient.age,
                'sex': patient.sex.capitalize(),
                'date_of_birth': patient.date_of_birth.isoformat(),
                'blood_type': patient.blood_type,
                'address': patient.address,
                'barangay': patient.barangay,
                'allergies': patient.allergies,
                'emergency_contact_name': patient.emergency_contact_name,
                'emergency_contact_number': patient.emergency_contact_number,
            },
            'records': record_list
        })

    elif request.method == 'PUT':
        data = json.loads(request.body)

        MedicalRecord.objects.create(
            patient=patient,
            attending_staff=request.user,
            visit_date=data.get('visit_date', timezone.now().date()),
            appointment_time=data.get('appointment_time'),
            status=data.get('status', 'COMPLETED'),
            blood_pressure=data.get('blood_pressure', ''),
            temperature=data.get('temperature'),
            weight=data.get('weight'),
            diagnosis=data.get('diagnosis', ''),
            treatment=data.get('treatment', ''),
            prescription=data.get('prescription', ''),
            notes=data.get('notes', ''),
            follow_up_date=data.get('follow_up_date'),
        )

        return JsonResponse({"message": "Medical record added successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def schedule(request):
    """GET — upcoming follow-ups for the logged-in staff member."""
    if request.method == 'GET':
        upcoming_records = MedicalRecord.objects.select_related(
            'patient__user'
        ).filter(
            attending_staff=request.user,
            follow_up_date__isnull=False,
            follow_up_date__gte=timezone.now().date(),
        ).order_by('follow_up_date')

        schedule_list = [
            {
                'patient_name': r.patient.user.get_full_name(),
                'follow_up_date': r.follow_up_date.isoformat(),
                'diagnosis': r.diagnosis,
                'notes': r.notes,
            }
            for r in upcoming_records
        ]

        return JsonResponse({'schedule': schedule_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def schedule_history(request):
    """GET — past visit history for the logged-in staff member."""
    if request.method == 'GET':
        past_records = MedicalRecord.objects.select_related(
            'patient__user'
        ).filter(
            attending_staff=request.user
        ).order_by('-visit_date')

        history_list = [
            {
                'patient_name': r.patient.user.get_full_name(),
                'visit_date': r.visit_date.isoformat(),
                'diagnosis': r.diagnosis,
                'treatment': r.treatment,
                'follow_up_date': r.follow_up_date.isoformat() if r.follow_up_date else None,
            }
            for r in past_records
        ]

        return JsonResponse({'history': history_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)