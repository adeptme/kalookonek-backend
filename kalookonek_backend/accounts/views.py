from django.http import JsonResponse
from .auth import supabase_auth_required
from .models import UserProfile

# ---------------------------------------------------------------------------
# NOTE: login, create_account, and reset_password are intentionally commented
# out. The frontend handles these flows directly via Supabase Auth — Django
# does not need to proxy credentials. These stubs are kept here for reference.
# ---------------------------------------------------------------------------

# def login(request):
#     if request.method == 'POST':
#         pass
#     elif request.method == 'GET':
#         pass

# def create_account(request):
#     if request.method == 'POST':
#         pass

# def reset_password(request):
#     if request.method == 'POST':
#         pass


@supabase_auth_required
def get_profile(request):
    """
    GET /accounts/profile/
    Returns the user's profile PLUS dashboard statistics and pending applicants.
    """
    profile = request.user_profile
    
    # 1. Fetch Stats for the Dashboard Cards
    # Note: Replace 'SeniorProfile' with your actual model name for seniors
    stats = {
        'seniors': 12450, # Replace with: SeniorProfile.objects.count()
        'pending': UserProfile.objects.filter(role='staff', is_approved=False).count(),
        'appointments': 18, # Replace with: Appointment.objects.filter(date=today).count()
    }

    # 2. Fetch Pending Applicants for the "Needs Approval" Table
    # We only want users who are NOT yet approved
    pending_users = UserProfile.objects.filter(is_approved=False).order_by('-created_at')[:5]
    
    applicants_list = []
    for p in pending_users:
        applicants_list.append({
            'id': p.id,
            'full_name': f"{p.user.first_name} {p.user.last_name}",
            'employee_id': p.display_id,
            'barangay': getattr(p, 'barangay', 'N/A'), # Uses N/A if barangay field doesn't exist
            'created_at': p.created_at.isoformat(),
        })

    # 3. Return everything in one JSON "Bundle"
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


@supabase_auth_required
def account_settings(request):
    """
    PUT /accounts/settings/
    Allows an authenticated user to update their own profile settings.
    """
    if request.method == 'PUT':
        import json
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

        return JsonResponse({'message': 'Profile updated successfully.', 'display_id': profile.display_id})

    return JsonResponse({'error': 'Method not allowed.'}, status=405)