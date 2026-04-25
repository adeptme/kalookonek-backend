import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .auth import supabase_auth_required
from .models import RegistrationRequest

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


@csrf_exempt
def request_access(request):
    """
    POST /accounts/request-access/
    Public endpoint (no auth required).
    The frontend 'Request Access' form submits here instead of inserting
    directly into the Supabase profiles table.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        employee_id = data.get('employee_id', '').strip()
        barangay = data.get('barangay', '').strip()
        role_requested = data.get('role_requested', 'staff').strip()

        if not first_name or not last_name or not email:
            return JsonResponse({'error': 'first_name, last_name, and email are required.'}, status=400)

        # Prevent duplicate pending requests for the same email
        if RegistrationRequest.objects.filter(email=email, status='PENDING').exists():
            return JsonResponse({'error': 'A pending request for this email already exists.'}, status=409)

        reg_request = RegistrationRequest.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            employee_id=employee_id,
            barangay=barangay,
            role_requested=role_requested,
        )

        return JsonResponse({
            'message': 'Access request submitted successfully. You will be notified once approved.',
            'request_id': reg_request.id,
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)