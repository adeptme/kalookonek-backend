import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.contrib.auth.models import User
from kalookonek_backend.accounts.models import UserProfile
from kalookonek_backend.accounts.auth import role_required, supabase_auth_required
from .models import Announcement, AppointmentRequest, RefillRequest
from kalookonek_backend.mp.models import PatientProfile, MedicalRecord
from django.conf import settings
from django.contrib.admin.models import LogEntry


@role_required('admin')
def dashboard(request):
    if request.method == 'GET':
        total_users = User.objects.count()
        total_patients = PatientProfile.objects.count()
        pending_appointments = AppointmentRequest.objects.filter(
            status='PENDING').count()
        pending_refills = RefillRequest.objects.filter(
            status='PENDING').count()
        recent_announcements = Announcement.objects.select_related(
            'author').order_by('-created_at')[:5]

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

        LogEntry.objects.create(
            user=request.user,
            action_flag=2,  # CHANGE
            object_repr=user.first_name + " " + user.last_name,
            change_message=f"Admin profile updated for {user.email}",
            content_type_id=7,
        )

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
                "age": p.age,
                "dob": p.dob.strftime('%m/%d/%Y') if p.dob else None,
                "gender": p.gender,
                "barangay": p.barangay,
            }
            for p in profiles
        ]
        return JsonResponse({"users": user_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@role_required('admin')
def user_detail(request, display_id):
    """GET/PUT/DELETE a user by their display_id."""
    try:
        profile = UserProfile.objects.select_related(
            'user').get(display_id=display_id)
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
            "age": profile.age,
            "dob": profile.dob.strftime('%m/%d/%Y') if profile.dob else None,
            "gender": profile.gender,
            "barangay": profile.barangay,
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

        LogEntry.objects.create(
            user=request.user,
            action_flag=2,  # CHANGE
            object_repr=request.user.first_name + " " + request.user.last_name,
            change_message=f"Admin {request.user.email} updated user {target_user.email}'s profile.",
            content_type_id=7,
        )

        return JsonResponse({"message": "User updated successfully."})

    elif request.method == 'DELETE':
        LogEntry.objects.create(
            user=request.user,
            action_flag=3,  # DELETION
            object_repr=request.user.first_name + " " + request.user.last_name,
            change_message=f"Admin {request.user.email} deleted user {target_user.email}.",
            content_type_id=7,
        )
        target_user.delete()
        return JsonResponse({"message": "User deleted successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
def announcements(request):
    """
    GET — public, returns all announcements.
    POST — requires staff/admin, creates an announcement.
    """
    if request.method == 'GET':
        category_filter = request.GET.get('category', '').strip()
        priority_filter = request.GET.get('priority', '').strip()

        announcements_qs = Announcement.objects.select_related('author').all()

        if category_filter:
            announcements_qs = announcements_qs.filter(category=category_filter)

        if priority_filter:
            announcements_qs = announcements_qs.filter(priority=priority_filter)

        announcement_list = [
            {
                "id": a.id,
                "title": a.title,
                "body": a.body,
                "category": a.category,
                "priority": a.priority,
                "author": a.author.get_full_name() if a.author else "Unknown",
                "is_published": a.is_published,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in announcements_qs
        ]

        return JsonResponse({"announcements": announcement_list}, status=200)

    if request.method == 'POST':
        return create_announcement(request)

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
@role_required('staff', 'admin')
def create_announcement(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    title = data.get("title", "").strip()
    body = data.get("body", "").strip()
    category = data.get("category", "General").strip()
    priority = data.get("priority", "Standard Information").strip()
    is_published = data.get("is_published", True)

    valid_categories = [
        "Health & Wellness",
        "Pension Update",
        "Events",
        "Emergency",
        "General",
    ]

    valid_priorities = [
        "Standard Information",
        "Urgent",
        "High Priority",
    ]

    if not title or not body:
        return JsonResponse({"error": "Title and body are required."}, status=400)

    if category not in valid_categories:
        return JsonResponse({"error": "Invalid category."}, status=400)

    if priority not in valid_priorities:
        return JsonResponse({"error": "Invalid priority."}, status=400)

    try:
        new_announcement = Announcement.objects.create(
            title=title,
            body=body,
            category=category,
            priority=priority,
            author=request.user,
            is_published=is_published,
            published_at=timezone.now() if is_published else None
        )

        return JsonResponse({
            "message": "Announcement created successfully.",
            "announcement": {
                "id": new_announcement.id,
                "title": new_announcement.title,
                "body": new_announcement.body,
                "category": new_announcement.category,
                "priority": new_announcement.priority,
                "author": new_announcement.author.get_full_name() if new_announcement.author else "Unknown",
                "is_published": new_announcement.is_published,
                "published_at": new_announcement.published_at.isoformat() if new_announcement.published_at else None,
                "created_at": new_announcement.created_at.isoformat(),
            }
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
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
            "category": item.category,
            "priority": item.priority,
            "author": item.author.get_full_name() if item.author else "Unknown",
            "is_published": item.is_published,
            "created_at": item.created_at.isoformat(),
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

    LogEntry.objects.create(
        user=request.user,
        action_flag=2,  # CHANGE
        object_repr= request.user.first_name + " " + request.user.last_name,
        change_message=f"Announcement '{item.title}' updated by {request.user.email}. Title is: '{item.title}'.",
        content_type_id=10,
    )
    return JsonResponse({"message": "Announcement updated successfully."})


@role_required('staff', 'admin')
def _delete_announcement(request, item):
    item.delete()
    
    LogEntry.objects.create(
        user=request.user,
        action_flag=3,  # DELETION
        object_repr=request.user.first_name + " " + request.user.last_name,
        change_message=f"Announcement '{item.title}' deleted by {request.user.email}. Title was: '{item.title}'",
        content_type_id=10,
    )

    return JsonResponse({"message": "Announcement deleted successfully."})


@role_required('admin')
def appointment_requests(request):
    """
    GET — list all appointment requests (optionally filter by status).
    """
    if request.method == 'GET':
        status_filter = request.GET.get('status', None)
        qs = AppointmentRequest.objects.select_related(
            'patient__user').order_by('-created_at')

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

@csrf_exempt
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

        # --- THE BRIDGE: Create a MedicalRecord in 'mp' app if approved ---
        if new_status == 'APPROVED':
            try:
                # Check if a scheduled record already exists for this exact request
                # (Optional safety check to prevent double-creation)
                MedicalRecord.objects.get_or_create(
                    patient=ar.patient,
                    visit_date=ar.requested_date,
                    appointment_time=ar.requested_time,
                    defaults={
                        'status': 'SCHEDULED',
                        'notes': f"Auto-scheduled from request: {ar.reason}"
                    }
                )
                LogEntry.objects.create(
                    user=request.user,
                    action_flag=1,  # ADDITION
                    object_repr=request.user.first_name + " " + request.user.last_name,
                    change_message=f"MedicalRecord auto-created for {ar.patient.user.email} on {ar.requested_date} from approved appointment request.",
                    content_type_id=7,
                )
            except Exception as e:
                LogEntry.objects.create(
                    user=request.user,
                    action_flag=3,  # DELETION
                    object_repr=request.user.first_name + " " + request.user.last_name,
                    change_message=f"Failed to auto-create MedicalRecord for {ar.patient.user.email} on {ar.requested_date} from approved appointment request.",
                    content_type_id=7,
                )
                pass

        return JsonResponse({"message": f"Appointment request {new_status.lower()} successfully."})

    return JsonResponse({"error": "Method not allowed."}, status=405)

@csrf_exempt
@role_required('admin')
def admin_logs(request):
    """
    GET — return recent Django admin/system logs.
    """
    if request.method == 'GET':
        logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:100]

        log_list = [
            {
                "id": log.id,
                "user": log.object_repr,
                "action_time": log.action_time.isoformat(),
                "content_type": log.content_type.name if log.content_type else "System",
                "object_repr": log.object_repr,
                "action_flag": str(log.get_action_flag_display()),
                "user_id": log.user_id
            }
            for log in logs
        ]

        return JsonResponse({"logs": log_list}, status=200)

    return JsonResponse({"error": "Method not allowed."}, status=405)

# ---------------------------------------------------------------------------
# Registration Request Management (uses UserProfile.is_approved)
# ---------------------------------------------------------------------------

@role_required('admin', 'staff')
def registration_requests(request):
    """
    GET — list all pending registration requests (unapproved UserProfiles).
    Optionally filter: ?status=pending or ?status=approved
    """
    if request.method == 'GET':
        status_filter = request.GET.get('status', '').lower()

        if status_filter == 'approved':
            qs = UserProfile.objects.filter(is_approved=True)
        elif status_filter == 'pending' or not status_filter:
            qs = UserProfile.objects.filter(is_approved=False)
        else:
            qs = UserProfile.objects.all()

        qs = qs.select_related('user').order_by('-created_at')

        request_list = [
            {
                "id": p.id,
                "display_id": p.display_id,
                "first_name": p.user.first_name,
                "last_name": p.user.last_name,
                "email": p.user.email,
                "role": p.role,
                "is_approved": p.is_approved,
                "age": p.age,
                "dob": p.dob.strftime('%m/%d/%Y') if p.dob else None,
                "gender": p.gender,
                "barangay": p.barangay,
                "created_at": p.created_at.isoformat(),
            }
            for p in qs
        ]
        print(request_list)
        return JsonResponse({"registration_requests": request_list})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
@role_required('admin')
def registration_request_approve(request, id):
    try:
        profile = UserProfile.objects.select_related('user').get(id=id)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "Registration request not found."}, status=404)

    if request.method not in ('POST', 'PUT'):
        return JsonResponse({"error": "Method not allowed."}, status=405)

    if profile.is_approved:
        return JsonResponse({"error": "This user is already approved."}, status=400)

    temp_password = None

    if not profile.supabase_uid:
        try:
            from supabase import create_client

            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
                return JsonResponse({
                    "error": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend .env."
                }, status=500)

            supabase_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )

            first = profile.user.first_name.replace(" ", "").capitalize()
            last = profile.user.last_name.replace(" ", "").capitalize()
            temp_password = f"{first}{last}123!"

            res = supabase_client.auth.admin.create_user({
                'email': profile.user.email,
                'password': temp_password,
                'email_confirm': True,
                'user_metadata': {
                    'full_name': f"{profile.user.first_name} {profile.user.last_name}".strip()
                }
            })

            profile.supabase_uid = res.user.id
            LogEntry.objects.create(
                user=request.user,
                action_flag=1,  # ADDITION
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"Supabase Auth user created for {profile.user.email} during approval.",
                content_type_id=14,
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Supabase create_user failed during approval for {profile.user.email}: {e}")
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,  # DELETION
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"Failed to create Supabase Auth user for {profile.user.email} during approval.",
                content_type_id=14,
            )
            return JsonResponse({
                "error": f"Failed to create Supabase account: {str(e)}"
            }, status=500)

    profile.is_approved = True
    profile.save()

    if profile.role == 'patient':
            
            PatientProfile.objects.get_or_create(
                user=profile.user,
                defaults={
                    'date_of_birth': profile.dob or timezone.now().date(),
                    'sex': profile.gender.lower() if profile.gender else 'other',
                    'barangay': profile.barangay or '',
                    'address': profile.barangay or '' # Placeholder
                }
            )


    msg = "Request approved."
    if temp_password:
        msg += f" Account created with temporary password: {temp_password}"
    else:
        msg += " User can now log in with their chosen password."

    LogEntry.objects.create(
        user=request.user,
        action_flag=2,  # CHANGE
        object_repr=request.user.first_name + " " + request.user.last_name,
        change_message=f"Approved registration request for {profile.user.email}.",
        content_type_id=14,
    )

    return JsonResponse({
        "message": msg,
        "display_id": profile.display_id,
        "email": profile.user.email,
        "temporary_password": temp_password
    }, status=200)


@csrf_exempt
@role_required('admin')
def registration_request_reject(request, id):
    """
    PUT — reject a registration request.
    Deletes the unapproved UserProfile and Django User.
    """
    try:
        profile = UserProfile.objects.select_related('user').get(id=id)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "Registration request not found."}, status=404)

    if profile.is_approved:
        return JsonResponse({"error": "Cannot reject an already approved user."}, status=400)

    if request.method == 'PUT':
        email = profile.user.email
        LogEntry.objects.create(
            user=request.user,
            action_flag=3,  # DELETION
            object_repr=request.user.first_name + " " + request.user.last_name,
            change_message=f"Rejected registration request for {email} and deleted the user.",
            content_type_id=14,
        )
        profile.user.delete()  # Cascades to delete the UserProfile too
        return JsonResponse({"message": f"Registration request for {email} rejected and removed."})

    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
@role_required('admin')
def admin_create_account(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', '').strip().lower()

        if not email or not password or not first_name or not last_name:
            return JsonResponse({
                'error': 'email, password, first_name, and last_name are required.'
            }, status=400)

        if len(password) < 6:
            return JsonResponse({'error': 'Password must be at least 6 characters.'}, status=400)

        valid_roles = ('patient', 'staff', 'admin')
        if role not in valid_roles:
            return JsonResponse({
                'error': f"role must be one of: {', '.join(valid_roles)}"
            }, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'An account with this email already exists.'}, status=409)

        try:
            from supabase import create_client
            from django.conf import settings as django_settings
            supabase_client = create_client(
                django_settings.SUPABASE_URL, django_settings.SUPABASE_SERVICE_ROLE_KEY)
            res = supabase_client.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {
                    'full_name': f"{first_name} {last_name}".strip()
                }
            })
            supabase_uid = res.user.id
            LogEntry.objects.create(
                user=request.user,
                action_flag=1,  # ADDITION
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"{role.capitalize()} account created for {email} by admin {request.user.email}.",
                content_type_id=7,
            )
            
        except Exception as e:
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,  # DELETION
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"Failed to create {role.capitalize()} account for {email} by admin {request.user.email}.",
                content_type_id=7,
            )
            return JsonResponse({'error': f'Failed to create Supabase account: {str(e)}'}, status=500)

        try:
            django_user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            profile = UserProfile.objects.create(
                user=django_user,
                role=role,
                supabase_uid=supabase_uid,
                is_approved=True,  # Admin-created accounts are auto-approved
            )
        except Exception as db_err:

            try:
                supabase_client.auth.admin.delete_user(supabase_uid)
                LogEntry.objects.create(
                    user=request.user,
                    action_flag=3,  # DELETION
                    object_repr=request.user.first_name + " " + request.user.last_name,
                    change_message=f"Rolled back Supabase user {supabase_uid} after Django DB failure for {email}.",
                    content_type_id=7,
                )
            except Exception:
                pass
            
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,  # DELETION
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"Django DB error while admin-creating account for {email}: {db_err}",
                content_type_id=7,
            )
            return JsonResponse({'error': f'Account creation failed: {str(db_err)}'}, status=500)

        LogEntry.objects.create(
            user=request.user,
            action_flag=1,  # ADDITION
            object_repr=request.user.first_name + " " + request.user.last_name,
            change_message=f"Admin {request.user.email} created {role} account for {email} with display_id {profile.display_id}.",
            content_type_id=7,
        )

        return JsonResponse({
            'message': f'{role.capitalize()} account created successfully.',
            'display_id': profile.display_id,
            'email': email,
            'role': role,
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)

@csrf_exempt
@role_required('admin')
def get_staff_accounts(request):
    if request.method == 'GET':
        staff_accounts = UserProfile.objects.filter(
            role__in=['staff', 'admin']
        ).select_related('user')

        data = []

        for profile in staff_accounts:
            if profile.user.is_superuser:
                continue

            data.append({
                'display_id': profile.display_id,
                'email': profile.user.email,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'role': profile.role,
                'is_active': profile.user.is_active,
                'is_approved': profile.is_approved
            })

        return JsonResponse({'staff_accounts': data}, status=200)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            display_id = data.get('display_id')

            if not display_id:
                return JsonResponse({'error': 'display_id is required.'}, status=400)

            try:
                profile = UserProfile.objects.select_related('user').get(display_id=display_id)
            except UserProfile.DoesNotExist:
                return JsonResponse({'error': 'User not found.'}, status=404)

            if profile.role not in ['staff', 'admin']:
                return JsonResponse({'error': 'User is not a staff or admin account.'}, status=400)

            target_user = profile.user

            target_user.first_name = data.get('first_name', target_user.first_name)
            target_user.last_name = data.get('last_name', target_user.last_name)
            target_user.email = data.get('email', target_user.email)

            if 'is_active' in data:
                target_user.is_active = data.get('is_active')

            if 'role' in data:
                new_role = data.get('role')
                if new_role not in ['staff', 'admin']:
                    return JsonResponse({'error': 'Role must be staff or admin.'}, status=400)
                profile.role = new_role

            target_user.save()
            profile.save()

            LogEntry.objects.create(
                user=request.user,
                action_flag=2,  # CHANGE
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"Admin {request.user.email} updated user {target_user.email}'s profile.",
                content_type_id=7,
            )

            return JsonResponse({'message': f"User {target_user.email} updated successfully."}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            display_id = data.get('display_id')

            if not display_id:
                return JsonResponse({'error': 'display_id is required.'}, status=400)

            profile = UserProfile.objects.select_related('user').get(display_id=display_id)

            if profile.role not in ['staff', 'admin']:
                return JsonResponse({'error': 'User is not a staff or admin account.'}, status=400)

            target_user = profile.user
            email = target_user.email

            target_user.is_active = False
            target_user.save()

            LogEntry.objects.create(
                user=request.user,
                action_flag=2,  # CHANGE
                object_repr=request.user.first_name + " " + request.user.last_name,
                change_message=f"Admin {request.user.email} deactivated user {target_user.email}.",
                content_type_id=7,
            )

            return JsonResponse({'message': f"User {email} deactivated successfully."}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except UserProfile.DoesNotExist:
            return JsonResponse({'error': 'User not found.'}, status=404)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"message": "CSRF cookie set"})
