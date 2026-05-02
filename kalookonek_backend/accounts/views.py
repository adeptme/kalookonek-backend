import json
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from .auth import supabase_auth_required
from .models import UserProfile

# ---------------------------------------------------------------------------
# CORE DASHBOARD VIEWS
# ---------------------------------------------------------------------------


@supabase_auth_required
def get_profile(request):
    """
    GET /accounts/profile/
    Returns the user's profile, dashboard statistics, and pending staff applicants.
    """
    profile = request.user_profile

    stats = {
        'seniors': UserProfile.objects.filter(role='patient').count(),
        'pending': UserProfile.objects.filter(role='staff', is_approved=False).count(),
        'appointments': 18,
    }

    pending_users = UserProfile.objects.filter(
        is_approved=False).order_by('-created_at')[:5]

    applicants_list = []
    for p in pending_users:
        applicants_list.append({
            'id': p.id,
            'full_name': f"{p.user.first_name} {p.user.last_name}",
            'employee_id': p.display_id,
            'barangay': getattr(p, 'barangay', 'N/A'),
            'created_at': p.created_at.isoformat(),
        })

    return JsonResponse({
        'user': {
            'display_id': profile.display_id,
            'email': request.user.email,
            'full_name': request.user.get_full_name() or "Raphael Espiritu",
            'role': profile.role,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        },
        'stats': stats,
        'applicants': applicants_list
    })

# ---------------------------------------------------------------------------
# PATIENT MANAGEMENT VIEWS
# ---------------------------------------------------------------------------


@supabase_auth_required
def get_recent_patients(request):
    """
    GET /accounts/patients/?search=query
    Fetches the 10 most recent patients for the Dashboard table.
    """
    search_query = request.GET.get('search', '').strip()
    patients_qs = UserProfile.objects.filter(role='patient')

    if search_query:
        patients_qs = patients_qs.filter(
            Q(display_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    recent_patients = patients_qs.order_by('-created_at')[:10]

    patients_list = []
    for p in recent_patients:
        full_name = f"{p.user.first_name} {p.user.last_name}".strip(
        ) or p.user.username
        patients_list.append({
            'id': p.display_id,
            'name': full_name,
            'time': p.created_at.strftime('%I:%M %p'),
            'purpose': 'Medical Record',
            'status': 'COMPLETED' if p.updated_at else 'PENDING'
        })

    return JsonResponse(patients_list, safe=False)


@supabase_auth_required
def get_all_patients(request):
    """
    GET /accounts/directory/?search=...&barangay=...&status=...
    Fetches all patients with support for Search, Barangay, and Status filters 
    specifically for the Patient Directory page.
    """
    # 1. Capture filter parameters from the frontend request
    search_query = request.GET.get('search', '').strip()
    barangay_filter = request.GET.get('barangay', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # 2. Start with all patients
    patients_qs = UserProfile.objects.filter(role='patient')

    # 3. Apply Search (Name or ID)
    if search_query:
        patients_qs = patients_qs.filter(
            Q(display_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    # 4. Apply Barangay Filter
    if barangay_filter and barangay_filter != "All Barangays":
        patients_qs = patients_qs.filter(barangay=barangay_filter)

    # 5. Apply Status Filter
    if status_filter == "COMPLETED":
        patients_qs = patients_qs.filter(updated_at__isnull=False)
    elif status_filter == "PENDING":
        patients_qs = patients_qs.filter(updated_at__isnull=True)

    # 6. Format response to match the Patient Directory UI (Screenshot (3426).png)
    patients_list = []
    for p in patients_qs.order_by('user__last_name'):
        patients_list.append({
            'id': p.display_id,
            'name': f"{p.user.first_name} {p.user.last_name}",
            'age': getattr(p, 'age', 'N/A'),
            'gender': getattr(p, 'gender', 'N/A'),
            'barangay': getattr(p, 'barangay', 'Brgy. Unset'),
            'last_visit': p.updated_at.strftime('%b %d, %Y') if p.updated_at else 'No visits yet',
            'status': 'COMPLETED' if p.updated_at else 'PENDING'
        })

    return JsonResponse(patients_list, safe=False)

# ---------------------------------------------------------------------------
# SETTINGS & AUTH STUBS
# ---------------------------------------------------------------------------


@supabase_auth_required
def account_settings(request):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        profile = request.user_profile
        user = request.user

        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone_number' in data:
            profile.phone_number = data['phone_number']

        user.save()
        profile.save()

        return JsonResponse({
            'message': 'Profile updated successfully.',
            'display_id': profile.display_id
        })

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        return JsonResponse({"status": "success"}, status=200)
    return JsonResponse({"error": "Method not allowed"}, status=405)
