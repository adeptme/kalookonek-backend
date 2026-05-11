import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.conf import settings
from .auth import supabase_auth_required
from .models import UserProfile

logger = logging.getLogger(__name__)



@csrf_exempt
def create_account(request):
    """
    POST /accounts/create/

    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()

        if not email or not password:
            return JsonResponse({'error': 'email and password are required.'}, status=400)

        if len(password) < 6:
            return JsonResponse({'error': 'Password must be at least 6 characters.'}, status=400)

        # Check for existing user
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'An account with this email already exists.'}, status=409)

        # --- Step 1: Create user in Supabase Auth ---
        try:
            from supabase import create_client
            supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            res = supabase_client.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {
                    'full_name': f"{first_name} {last_name}".strip()
                }
            })
            supabase_uid = res.user.id
            logger.info(f"Supabase user created for {email}, uid={supabase_uid}")
        except Exception as e:
            logger.error(f"Supabase create_user failed for {email}: {e}")
            return JsonResponse({'error': f'Failed to create account: {str(e)}'}, status=500)

        # --- Step 2: Create Django User + UserProfile ---
        try:
            django_user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            profile = UserProfile.objects.create(
                user=django_user,
                role='patient',
                supabase_uid=supabase_uid,
                is_approved=True,  # Patients are auto-approved
            )
        except Exception as db_err:
            # Roll back the Supabase user we just created so nothing is orphaned
            try:
                supabase_client.auth.admin.delete_user(supabase_uid)
                logger.warning(f"Rolled back Supabase user {supabase_uid} after Django DB failure.")
            except Exception:
                pass
            logger.error(f"Django DB error while creating account for {email}: {db_err}")
            return JsonResponse({'error': f'Account creation failed: {str(db_err)}'}, status=500)

        return JsonResponse({
            'message': 'Account created successfully.',
            'display_id': profile.display_id,
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@csrf_exempt
def request_access(request):
    """
    POST /accounts/request-access/

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
        role_requested = data.get('role_requested', 'staff').strip()

        if not first_name or not last_name or not email:
            return JsonResponse({'error': 'first_name, last_name, and email are required.'}, status=400)

        # Prevent duplicate pending requests
        if UserProfile.objects.filter(user__email=email, is_approved=False).exists():
            return JsonResponse({'error': 'A pending request for this email already exists.'}, status=409)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'An account with this email already exists.'}, status=409)

        # Create a Django User + unapproved UserProfile (no Supabase account yet)
        try:
            django_user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            profile = UserProfile.objects.create(
                user=django_user,
                role=role_requested if role_requested in ('staff', 'admin') else 'staff',
                is_approved=False,  # Awaiting admin approval
            )
        except Exception as db_err:
            logger.error(f"Django DB error while creating access request for {email}: {db_err}")
            return JsonResponse({'error': f'Access request failed: {str(db_err)}'}, status=500)

        return JsonResponse({
            'message': 'Access request submitted successfully. You will be notified once approved.',
            'display_id': profile.display_id,
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@supabase_auth_required
def get_profile(request):
    """
    GET /accounts/profile/
    Returns the user's profile PLUS dashboard statistics and pending applicants.
    """
    profile = request.user_profile

    # 1. Fetch Stats for the Dashboard Cards
    stats = {
        'seniors': UserProfile.objects.filter(role='patient', is_approved=True).count(),
        'pending': UserProfile.objects.filter(is_approved=False).count(),
        'appointments': 18,  # Replace with: Appointment.objects.filter(date=today).count()
    }

    # 2. Fetch Pending Applicants for the "Needs Approval" Table
    pending_users = UserProfile.objects.filter(is_approved=False).select_related('user').order_by('-created_at')[:5]

    applicants_list = []
    for p in pending_users:
        applicants_list.append({
            'id': p.id,
            'full_name': f"{p.user.first_name} {p.user.last_name}",
            'employee_id': p.display_id,
            'barangay': getattr(p, 'barangay', 'N/A'),
            'created_at': p.created_at.isoformat(),
        })

    # 3. Return everything in one JSON "Bundle"
    return JsonResponse({
        'user': {
            'display_id': profile.display_id,
            'email': request.user.email,
            'full_name': request.user.get_full_name(),
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