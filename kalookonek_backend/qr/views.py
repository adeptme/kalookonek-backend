from io import BytesIO
from urllib.parse import urljoin, urlparse, urlunparse

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, Signer, TimestampSigner
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.models import User

import qrcode

from kalookonek_backend.accounts.auth import role_required, supabase_auth_required
from kalookonek_backend.accounts.models import UserProfile
from kalookonek_backend.mp.models import MedicalRecord, PatientProfile


QR_FULL_TTL_SECONDS = getattr(settings, "QR_FULL_TTL_SECONDS", 900)


def _get_patient_by_display_id(display_id):
    try:
        profile = UserProfile.objects.select_related("user").get(display_id=display_id, role="patient")
    except UserProfile.DoesNotExist:
        return None, None

    #try:
    #    patient = PatientProfile.objects.get(user=profile.user)
    #except PatientProfile.DoesNotExist:
    #    return None, None

    #return patient, profile
    return None, profile


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


def _build_scan_url(request, view_name, token):
    path = reverse(view_name, kwargs={"token": token})
    base_url = getattr(settings, "QR_BASE_URL", None)
    if base_url:
        return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

    scan_url = request.build_absolute_uri(path)
    if getattr(settings, "QR_FORCE_HTTPS", False):
        parsed = urlparse(scan_url)
        if parsed.scheme != "https":
            parsed = parsed._replace(scheme="https")
            scan_url = urlunparse(parsed)
    return scan_url

@supabase_auth_required
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
    scan_url = _build_scan_url(request, "qr_scan_basic", token)

    png_bytes = _build_qr_png(scan_url)
    return HttpResponse(png_bytes, content_type="image/png")


@supabase_auth_required
@role_required("patient", "Patient")
def qr_code_png_full(request):
    user = request.user
    try:
        current_display_id = UserProfile.objects.get(user=request.user).display_id
    except UserProfile.DoesNotExist:
        return HttpResponse("User profile not found", status=404)

    signer = TimestampSigner()
    token = signer.sign(current_display_id)
    scan_url = _build_scan_url(request, "qr_scan_full", token)

    png_bytes = _build_qr_png(scan_url)
    return HttpResponse(png_bytes, content_type="image/png")


def qr_scan_basic(request, token):
    signer = Signer()
    try:
        display_id = signer.unsign(token)
    except SignatureExpired:
        return HttpResponse("QR code expired", status=410)
    except BadSignature:
        return HttpResponse("Invalid QR code", status=400)
    patient, profile = _get_patient_by_display_id(display_id)
    if not patient:
        return HttpResponse("Patient Record not found or non-existent.", status=404)

    context = {
        "patient_data": {
            "first_name": profile.user.first_name,
            "last_name": profile.user.last_name,
            "age": profile.calculated_age if profile else None,
            "sex": patient.sex,
            "date_of_birth": patient.date_of_birth,
            "blood_type": patient.blood_type,
            "address": patient.address,
            "barangay": getattr(profile, "barangay", "N/A"),
            "emergency_contact_name": getattr(patient, "emergency_contact_name", "N/A"),
            "emergency_contact_number": getattr(patient, "emergency_contact_number", "N/A"),
            "allergies": getattr(patient, "allergies", "N/A"),
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
        return HttpResponse("Patient Record not found or non-existent.", status=404)

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