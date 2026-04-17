import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
from kalookonek_backend.accounts.models import UserProfile
from kalookonek_backend.accounts.auth import role_required, supabase_auth_required
from .models import Announcement, AppointmentRequest, RefillRequest
from kalookonek_backend.mp.models import PatientProfile


@role_required('admin')
def dashboard(request):
    if request.method == 'GET':
        total_users = User.objects.count()
        total_patients = PatientProfile.objects.count()
        pending_appointments = AppointmentRequest.objects.filter(status='PENDING').count()
        pending_refills = RefillRequest.objects.filter(status='PENDING').count()
        recent_announcements = Announcement.objects.select_related('author').order_by('-created_at')[:5]

        announcement_list = [
            {
                "id": a.id,
                "title": a.title,
                "author": a.author.get_full_name() if a.author else "Unknown",
                "is_published": a.is_published,
                "date": a.created_at.strftime('%Y-%m-%d')
            }
            for a in recent_announcements
        ]

        return JsonResponse({
            "total_users": total_users,
            "total_patients": total_patients,
            "pending_appointments": pending_appointments,
            "pending_refills": pending_refills,
            "recent_announcements": announcement_list
        })

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def admin_profile(request):
    """GET/PUT the admin's own profile."""
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

        return JsonResponse({"message": "Admin profile updated successfully"})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def all_users(request):
    """GET — list all users with their display_id."""
    if request.method == 'GET':
        profiles = UserProfile.objects.select_related('user').all()
        user_list = [
            {
                "display_id": p.display_id,
                "name": p.user.get_full_name(),
                "email": p.user.email,
                "role": p.role,
                "is_active": p.user.is_active,
            }
            for p in profiles
        ]
        return JsonResponse({"users": user_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def user_detail(request, display_id):
    """GET/PUT/DELETE a user by their display_id."""
    try:
        profile = UserProfile.objects.select_related('user').get(display_id=display_id)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)

    target_user = profile.user

    if request.method == 'GET':
        return JsonResponse({
            "display_id": profile.display_id,
            "first_name": target_user.first_name,
            "last_name": target_user.last_name,
            "email": target_user.email,
            "role": profile.role,
            "phone_number": profile.phone_number,
            "is_active": target_user.is_active,
        })

    elif request.method == 'PUT':
        data = json.loads(request.body)
        target_user.first_name = data.get('first_name', target_user.first_name)
        target_user.last_name = data.get('last_name', target_user.last_name)
        target_user.email = data.get('email', target_user.email)
        profile.role = data.get('role', profile.role)
        profile.phone_number = data.get('phone_number', profile.phone_number)

        if 'is_active' in data:
            target_user.is_active = data['is_active']

        target_user.save()
        profile.save()
        return JsonResponse({"message": "User updated successfully."})

    elif request.method == 'DELETE':
        target_user.delete()
        return JsonResponse({"message": "User deleted successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


def announcements(request):
    """
    GET — public, returns all announcements.
    POST — requires staff/admin, creates an announcement.
    """
    if request.method == 'GET':
        announcements_qs = Announcement.objects.select_related('author').all()
        announcement_list = [
            {
                "id": a.id,
                "title": a.title,
                "body": a.body,
                "author": a.author.get_full_name() if a.author else "Unknown",
                "is_published": a.is_published,
                "date": a.created_at.strftime('%Y-%m-%d'),
            }
            for a in announcements_qs
        ]
        return JsonResponse({"announcements": announcement_list})

    elif request.method == 'POST':
        return _create_announcement(request)

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def _create_announcement(request):
    """Internal helper — called from announcements() for POST."""
    data = json.loads(request.body)
    new_announcement = Announcement.objects.create(
        title=data.get('title', ''),
        body=data.get('body', ''),
        author=request.user,
        is_published=data.get('is_published', False),
        published_at=timezone.now() if data.get('is_published') else None
    )
    return JsonResponse({"message": "Announcement created successfully.", "id": new_announcement.id})


def announcement_detail(request, id):
    """
    GET — public.
    PUT/DELETE — requires staff/admin.
    """
    try:
        item = Announcement.objects.get(id=id)
    except Announcement.DoesNotExist:
        return JsonResponse({"error": "Announcement not found."}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "author": item.author.get_full_name() if item.author else "Unknown",
            "is_published": item.is_published,
            "date": item.created_at.strftime('%Y-%m-%d'),
        })

    elif request.method == 'PUT':
        return _update_announcement(request, item)

    elif request.method == 'DELETE':
        return _delete_announcement(request, item)

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('staff', 'admin')
def _update_announcement(request, item):
    data = json.loads(request.body)
    item.title = data.get('title', item.title)
    item.body = data.get('body', item.body)

    if data.get('is_published') and not item.is_published:
        item.publish()
    elif 'is_published' in data and not data.get('is_published'):
        item.is_published = False
        item.published_at = None

    item.save()
    return JsonResponse({"message": "Announcement updated successfully."})


@role_required('staff', 'admin')
def _delete_announcement(request, item):
    item.delete()
    return JsonResponse({"message": "Announcement deleted successfully."})


@role_required('admin')
def appointment_requests(request):
    """
    GET — list all appointment requests (optionally filter by status).
    """
    if request.method == 'GET':
        status_filter = request.GET.get('status', None)
        qs = AppointmentRequest.objects.select_related('patient__user').order_by('-created_at')

        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        request_list = [
            {
                "id": ar.id,
                "patient_name": ar.patient.user.get_full_name(),
                "requested_date": ar.requested_date.isoformat(),
                "requested_time": ar.requested_time.isoformat() if ar.requested_time else None,
                "reason": ar.reason,
                "status": ar.status,
                "created_at": ar.created_at.isoformat(),
            }
            for ar in qs
        ]
        return JsonResponse({"appointment_requests": request_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def appointment_request_detail(request, id):
    """
    PUT — approve or reject an appointment request.
    """
    try:
        ar = AppointmentRequest.objects.get(id=id)
    except AppointmentRequest.DoesNotExist:
        return JsonResponse({"error": "Appointment request not found."}, status=404)

    if request.method == 'PUT':
        data = json.loads(request.body)
        new_status = data.get('status', '').upper()

        if new_status not in ('APPROVED', 'REJECTED'):
            return JsonResponse({"error": "Status must be 'APPROVED' or 'REJECTED'."}, status=400)

        ar.status = new_status
        ar.save()
        return JsonResponse({"message": f"Appointment request {new_status.lower()} successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def refill_requests(request):
    """
    GET — list all refill requests (optionally filter by status).
    """
    if request.method == 'GET':
        status_filter = request.GET.get('status', None)
        qs = RefillRequest.objects.select_related('patient__user', 'medicine').order_by('-requested_at')

        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        request_list = [
            {
                "id": rr.id,
                "patient_name": rr.patient.user.get_full_name(),
                "medicine_name": rr.medicine.name,
                "status": rr.status,
                "requested_at": rr.requested_at.isoformat(),
                "processed_at": rr.processed_at.isoformat() if rr.processed_at else None,
            }
            for rr in qs
        ]
        return JsonResponse({"refill_requests": request_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def refill_request_detail(request, id):
    """
    PUT — approve or reject a refill request.
    """
    try:
        rr = RefillRequest.objects.get(id=id)
    except RefillRequest.DoesNotExist:
        return JsonResponse({"error": "Refill request not found."}, status=404)

    if request.method == 'PUT':
        data = json.loads(request.body)
        new_status = data.get('status', '').upper()

        if new_status not in ('APPROVED', 'REJECTED'):
            return JsonResponse({"error": "Status must be 'APPROVED' or 'REJECTED'."}, status=400)

        rr.status = new_status
        rr.processed_at = timezone.now()
        rr.save()
        return JsonResponse({"message": f"Refill request {new_status.lower()} successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)