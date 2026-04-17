from django.http import JsonResponse
from .auth import supabase_auth_required

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
    Returns the authenticated user's profile.
    The display_id is the human-readable identifier used for search on the frontend.
    """
    profile = request.user_profile
    return JsonResponse({
        'display_id': profile.display_id,       # e.g. "2026-001" — use this for search
        'email': request.user.email,
        'full_name': request.user.get_full_name(),
        'role': profile.role,
        'phone_number': profile.phone_number,
        'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        'created_at': profile.created_at.isoformat(),
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