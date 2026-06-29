import json
from django.http import JsonResponse
from django.utils import timezone
from kalookonek_backend.accounts.auth import supabase_auth_required
from kalookonek_backend.mp.models import PatientProfile, MedicalRecord
from kalookonek_backend.sysadmin.models import Announcement, AppointmentRequest, RefillRequest, Medicine


@supabase_auth_required
def dashboard(request):
    """
    GET — patient dashboard.
    Returns upcoming approved appointments, recent medical records, and published announcements.
    """
    if request.method == 'GET':
        profile = request.user_profile

        # Try to get the patient's PatientProfile
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            patient = None

        # Upcoming approved appointments
        upcoming_appointments = []
        if patient:
            upcoming_qs = AppointmentRequest.objects.filter(
                patient=patient,
                status='APPROVED',
                requested_date__gte=timezone.now().date(),
            ).order_by('requested_date')[:5]

            upcoming_appointments = [
                {
                    "id": ar.id,
                    "requested_date": ar.requested_date.isoformat(),
                    "requested_time": ar.requested_time.isoformat() if ar.requested_time else None,
                    "reason": ar.reason,
                    "status": ar.status,
                }
                for ar in upcoming_qs
            ]

        # Recent medical records
        recent_records = []
        if patient:
            records_qs = MedicalRecord.objects.filter(patient=patient).order_by('-visit_date')[:5]
            recent_records = [
                {
                    "id": r.id,
                    "visit_date": r.visit_date.isoformat(),
                    "diagnosis": r.diagnosis or "General Checkup",
                    "status": r.status,
                    "blood_pressure": r.blood_pressure,
                    "temperature": str(r.temperature) if r.temperature else None,
                    "weight": str(r.weight) if r.weight else None,
                    "attending_staff": r.attending_staff.get_full_name() if r.attending_staff else None,
                    "treatment": r.treatment,
                    "prescription": r.prescription,
                    "notes": r.notes,
                }
                for r in records_qs
            ]

        # Published announcements
        announcements_qs = Announcement.objects.filter(is_published=True).order_by('-published_at')[:5]
        announcements = [
            {
                "id": a.id,
                "title": a.title,
                "body": a.body,
                "date": a.published_at.strftime('%Y-%m-%d') if a.published_at else a.created_at.strftime('%Y-%m-%d'),
                "time": a.published_at.strftime('%I:%M %p') if a.published_at else a.created_at.strftime('%I:%M %p'),
            }
            for a in announcements_qs
        ]

        return JsonResponse({
            "display_id": profile.display_id,
            "name": request.user.get_full_name(),
            "upcoming_appointments": upcoming_appointments,
            "recent_records": recent_records,
            "announcements": announcements,
        })

    return JsonResponse({"error": "Method not allowed."}, status=405)


@supabase_auth_required
def user_profile(request):
    """
    GET — return own profile (UserProfile + PatientProfile if exists).
    PUT — update allowed profile fields.
    """
    profile = request.user_profile
    user = request.user

    if request.method == 'GET':
        # profile_picture is a TextField storing a URL string, not a FileField
        profile_pic_url = profile.profile_picture or None

        data = {
            "display_id": profile.display_id,
            "osca_id": profile.display_id,  # Alias for frontend compatibility
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": profile.role,
            "status": profile.status,
            "phone_number": profile.phone_number,
            "profile_picture": profile_pic_url,
        }

        # Include PatientProfile data if it exists
        try:
            patient = PatientProfile.objects.get(user=user)
            data["patient_info"] = {
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "age": patient.age,
                "sex": patient.sex,
                "blood_type": patient.blood_type,
                "address": patient.address,
                "barangay": patient.barangay,
                "emergency_contact_name": patient.emergency_contact_name,
                "emergency_contact_number": patient.emergency_contact_number,
                "allergies": patient.allergies,
                #notification
                "wants_push": getattr(patient, 'wants_push', True),
                "wants_sms": getattr(patient, 'wants_sms', True),
                "wants_email": getattr(patient, 'wants_email', False),
            }
        except PatientProfile.DoesNotExist:
            data["patient_info"] = None

        return JsonResponse(data)

    elif request.method in ['PUT', 'POST']:
        import logging
        logger = logging.getLogger(__name__)

        if request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.POST # Read the text fields
            logger.info(f"[PROFILE UPDATE] Multipart request. POST keys: {list(data.keys())}, FILES keys: {list(request.FILES.keys())}")
            
            # Upload profile picture to Supabase Storage
            if 'profile_picture' in request.FILES:
                uploaded_file = request.FILES['profile_picture']
                file_bytes = uploaded_file.read()
                file_ext = uploaded_file.name.rsplit('.', 1)[-1] if '.' in uploaded_file.name else 'jpg'
                content_type = uploaded_file.content_type or 'image/jpeg'
                logger.info(f"[PROFILE UPDATE] File received: name={uploaded_file.name}, size={len(file_bytes)} bytes, type={content_type}")
                
                try:
                    from supabase import create_client
                    from django.conf import settings
                    
                    supabase_client = create_client(
                        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                    
                    file_path = f"users/{user.id}/avatar.{file_ext}"
                    
                    # Upload to Supabase Storage (upsert overwrites existing)
                    supabase_client.storage.from_("profile-pictures").upload(
                        path=file_path,
                        file=file_bytes,
                        file_options={"content-type": content_type, "upsert": "true"}
                    )
                    
                    # Get the public URL and save it to the TextField
                    public_url = supabase_client.storage.from_("profile-pictures").get_public_url(file_path)
                    profile.profile_picture = public_url
                    logger.info(f"[PROFILE UPDATE] Upload success. URL saved: {public_url}")
                    
                except Exception as e:
                    logger.error(f"[PROFILE UPDATE] Supabase Storage upload FAILED: {e}")
                    return JsonResponse({'error': f'Image upload failed: {str(e)}'}, status=500)
            else:
                logger.info("[PROFILE UPDATE] No profile_picture in request.FILES — skipping image upload.")
        else:
            # If no image, handle it as normal JSON text
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone_number' in data:
            profile.phone_number = data['phone_number']

        # --- NOTIFICATION PREFERENCES LOGIC START ---
        if 'patient_info' in data:
            patient_info_data = data['patient_info']
            
            # If Axios/Fetch sent it as a stringified JSON (because of the image upload), parse it
            if isinstance(patient_info_data, str):
                try:
                    patient_info_data = json.loads(patient_info_data)
                except json.JSONDecodeError:
                    patient_info_data = {}
            
            try:
                patient = PatientProfile.objects.get(user=user)
                
                if 'wants_push' in patient_info_data:
                    patient.wants_push = patient_info_data['wants_push']
                if 'wants_sms' in patient_info_data:
                    patient.wants_sms = patient_info_data['wants_sms']
                if 'wants_email' in patient_info_data:
                    patient.wants_email = patient_info_data['wants_email']
                    
                patient.save()
            except PatientProfile.DoesNotExist:
                pass
        # --- NOTIFICATION PREFERENCES LOGIC END ---
        
        try:
            user.save()
            profile.save()
        except Exception as e:
            logger.error(f"[PROFILE UPDATE] Database save FAILED: {e}")
            return JsonResponse({'error': f'Profile save failed: {str(e)}'}, status=400)
        
        # profile_picture is a TextField, return it directly
        new_pic_url = profile.profile_picture or None

        logger.info(f"[PROFILE UPDATE] Complete. picture={new_pic_url}")
        return JsonResponse({
            "message": "Profile updated successfully.", 
            "display_id": profile.display_id,
            "profile_picture": new_pic_url
        })

    return JsonResponse({"error": "Method not allowed."}, status=405)


@supabase_auth_required
def health_record(request):
    """GET — return the logged-in patient's full medical record history."""
    if request.method == 'GET':
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            return JsonResponse({"error": "No patient profile found for this user."}, status=404)

        records = MedicalRecord.objects.filter(patient=patient).order_by('-visit_date')

        record_list = [
            {
                "id": r.id,
                "visit_date": r.visit_date.isoformat(),
                "attending_staff": r.attending_staff.get_full_name() if r.attending_staff else None,
                "status": r.status,
                "blood_pressure": r.blood_pressure,
                "temperature": str(r.temperature) if r.temperature else None,
                "weight": str(r.weight) if r.weight else None,
                "diagnosis": r.diagnosis,
                "treatment": r.treatment,
                "prescription": r.prescription,
                "notes": r.notes,
                "follow_up_date": r.follow_up_date.isoformat() if r.follow_up_date else None,
            }
            for r in records
        ]

        return JsonResponse({"records": record_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


def qr_code(request):
    """QR code generation — not yet implemented."""
    return JsonResponse({"message": "QR code feature not yet implemented."}, status=501)


@supabase_auth_required
def emergency_contacts(request):
    """
    GET — return emergency contact info from PatientProfile.
    PUT — update emergency contact info.
    """
    try:
        patient = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        return JsonResponse({"error": "No patient profile found for this user."}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_number": patient.emergency_contact_number,
        })

    elif request.method == 'PUT':
        data = json.loads(request.body)
        if 'emergency_contact_name' in data:
            patient.emergency_contact_name = data['emergency_contact_name']
        if 'emergency_contact_number' in data:
            patient.emergency_contact_number = data['emergency_contact_number']
        patient.save()
        return JsonResponse({"message": "Emergency contacts updated successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@supabase_auth_required
def medicine(request):
    """
    GET — list all available medicines.
    POST — create a refill request for the logged-in patient.
    """
    if request.method == 'GET':
        medicines = Medicine.objects.all()
        medicine_list = [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "stock_quantity": m.stock_quantity,
                "dosage_instructions": m.dosage_instructions,
            }
            for m in medicines
        ]
        return JsonResponse({"medicines": medicine_list})

    elif request.method == 'POST':
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            return JsonResponse({"error": "No patient profile found for this user."}, status=404)

        data = json.loads(request.body)
        medicine_id = data.get('medicine_id')

        if not medicine_id:
            return JsonResponse({"error": "medicine_id is required."}, status=400)

        try:
            med = Medicine.objects.get(id=medicine_id)
        except Medicine.DoesNotExist:
            return JsonResponse({"error": "Medicine not found."}, status=404)

        refill = RefillRequest.objects.create(
            patient=patient,
            medicine=med,
        )
        return JsonResponse({"message": "Refill request submitted successfully.", "id": refill.id})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@supabase_auth_required
def appointments(request):
    """
    GET — list the logged-in patient's appointment requests.
    POST — create a new appointment request.
    """
    try:
        patient = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        return JsonResponse({"error": "No patient profile found for this user."}, status=404)

    if request.method == 'GET':
        qs = AppointmentRequest.objects.filter(patient=patient).order_by('-created_at')
        appointment_list = [
            {
                "id": ar.id,
                "requested_date": ar.requested_date.isoformat(),
                "requested_time": ar.requested_time.isoformat() if ar.requested_time else None,
                "reason": ar.reason,
                "status": ar.status,
                "created_at": ar.created_at.isoformat(),
            }
            for ar in qs
        ]
        return JsonResponse({"appointments": appointment_list})

    elif request.method == 'POST':
        data = json.loads(request.body)

        requested_date = data.get('requested_date')
        reason = data.get('reason', '')

        if not requested_date:
            return JsonResponse({"error": "requested_date is required."}, status=400)

        ar = AppointmentRequest.objects.create(
            patient=patient,
            requested_date=requested_date,
            requested_time=data.get('requested_time'),
            reason=reason,
        )
        return JsonResponse({"message": "Appointment request submitted successfully.", "id": ar.id})

    return JsonResponse({"error": "Method not allowed."}, status=405)