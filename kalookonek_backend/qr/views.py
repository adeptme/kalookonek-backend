from io import BytesIO

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, Signer, TimestampSigner
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

import qrcode

from kalookonek_backend.accounts.auth import role_required
from kalookonek_backend.accounts.models import UserProfile
from kalookonek_backend.mp.models import MedicalRecord, PatientProfile


QR_FULL_TTL_SECONDS = getattr(settings, "QR_FULL_TTL_SECONDS", 900)


def _get_patient_by_display_id(display_id):
    try:
        profile = UserProfile.objects.select_related("user").get(display_id=display_id, role="patient")
    except UserProfile.DoesNotExist:
        return None, None

    try:
        patient = PatientProfile.objects.get(user=profile.user)
    except PatientProfile.DoesNotExist:
        return None, None

    return patient, profile


def _build_qr_png(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@role_required("patient", "Patient")
def qr_code_png_basic(request):
    
    user = request.user
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return HttpResponse("User profile not found", status=404)
    
    display_id = profile.display_id

    signer = Signer()
    token = signer.sign(display_id)
    scan_url = request.build_absolute_uri(reverse("qr_scan_basic", kwargs={"token": token}))

    png_bytes = _build_qr_png(scan_url)
    return HttpResponse(png_bytes, content_type="image/png")


@role_required("patient", "Patient")
def qr_code_png_full(request):
    current_display_id = None
    if hasattr(request, "user_profile"):
        current_display_id = request.user_profile.display_id
    elif getattr(request, "user", None) and request.user.is_authenticated:
        try:
            current_display_id = UserProfile.objects.get(user=request.user).display_id
        except UserProfile.DoesNotExist:
            current_display_id = None

    display_id = request.GET.get("display_id") or current_display_id
    if not display_id:
        return HttpResponse("Authentication required", status=401)

    if current_display_id is None or str(current_display_id) != str(display_id):
        return HttpResponse("Forbidden", status=403)

    patient, _profile = _get_patient_by_display_id(display_id)
    if not patient:
        return HttpResponse("Patient not found", status=404)

    signer = TimestampSigner()
    token = signer.sign(display_id)
    scan_url = request.build_absolute_uri(reverse("qr_scan_full", kwargs={"token": token}))

    png_bytes = _build_qr_png(scan_url)
    return HttpResponse(png_bytes, content_type="image/png")


def qr_scan_basic(request, token):
    signer = Signer()
    try:
        display_id = signer.unsign(token)
    except BadSignature:
        return HttpResponse("Invalid QR code", status=400)

    patient, profile = _get_patient_by_display_id(display_id)
    if not patient:
        return HttpResponse("Patient not found", status=404)

    context = {
        "patient_data": {
            "name": profile.user.get_full_name(),
            "sex": patient.sex,
            "date_of_birth": patient.date_of_birth,
            "blood_type": patient.blood_type,
            "address": patient.address,
            "barangay": patient.barangay,
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_number": patient.emergency_contact_number,
            "allergies": patient.allergies,
        }
    }

    return render(request, "qr/basic.html", context)


def qr_scan_full(request, token):
    signer = TimestampSigner()
    try:
        display_id = signer.unsign(token, max_age=QR_FULL_TTL_SECONDS)
    except SignatureExpired:
        return HttpResponse("QR code expired", status=410)
    except BadSignature:
        return HttpResponse("Invalid QR code", status=400)

    patient, profile = _get_patient_by_display_id(display_id)
    if not patient:
        return HttpResponse("Patient not found", status=404)

    medical_records = MedicalRecord.objects.filter(patient=patient).order_by("-created_at")

    context = {
        "patient_data": {
            "name": profile.user.get_full_name(),
            "sex": patient.sex,
            "date_of_birth": patient.date_of_birth,
            "blood_type": patient.blood_type,
            "address": patient.address,
            "barangay": patient.barangay,
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_number": patient.emergency_contact_number,
            "allergies": patient.allergies,
        },
        "records": medical_records,
    }

    return render(request, "qr/full.html", context)