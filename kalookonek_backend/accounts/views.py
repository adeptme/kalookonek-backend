import json
import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

# DRF Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Local Imports
from .auth import supabase_auth_required
from .models import UserProfile
from mp.models import MedicalRecord

logger = logging.getLogger(__name__)

@csrf_exempt
def create_account(request):
    """POST /accounts/create/ - Handles initial patient registration."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        gender = data.get('gender', '').strip() or None
        age_raw = data.get('age', None)
        dob_raw = data.get('dob', '').strip()
        barangay = data.get('barangay', '').strip() or None
        phone_number = data.get('phone_number', '').strip()[:11]

        if not email or not password or not first_name or not last_name:
            return JsonResponse({'error': 'email, password, first_name, and last_name are required.'}, status=400)

        dob = None
        if dob_raw:
            try:
                dob = datetime.strptime(dob_raw, '%m/%d/%Y').date()
            except ValueError:
                return JsonResponse({'error': 'dob must be in MM/DD/YYYY format.'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'An account with this email already exists.'}, status=409)

        try:
            from supabase import create_client
            from mp.models import PatientProfile
            
            supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            res = supabase_client.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {'full_name': f"{first_name} {last_name}".strip()}
            })
            supabase_uid = res.user.id

            django_user = User.objects.create_user(username=email, email=email, first_name=first_name, last_name=last_name)
            
            # Create the Identity Profile
            profile = UserProfile.objects.create(
                user=django_user, role='patient', supabase_uid=supabase_uid, 
                is_approved=False, dob=dob, gender=gender, barangay=barangay, phone_number=phone_number
            )
            
            return JsonResponse({'message': 'Registration submitted.', 'display_id': profile.display_id}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)

@csrf_exempt
def request_access(request):
    """POST /accounts/request-access/ - Handles Staff/Admin access requests."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        email = data.get('email', '').strip()
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already exists.'}, status=409)

        try:
            django_user = User.objects.create_user(
                username=email, email=email, 
                first_name=data.get('first_name'), last_name=data.get('last_name')
            )
            profile = UserProfile.objects.create(
                user=django_user, role=data.get('role_requested', 'staff'), is_approved=False
            )
            return JsonResponse({'message': 'Access request submitted.', 'display_id': profile.display_id}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)

@supabase_auth_required
def get_profile(request):
    """GET /accounts/profile/ - User dashboard stats."""
    profile = request.user_profile
    stats = {
        'seniors': UserProfile.objects.filter(role='patient', is_approved=True).count(),
        'pending': UserProfile.objects.filter(is_approved=False).count(),
        'appointments': MedicalRecord.objects.filter(visit_date=timezone.now().date()).count(),
    }
    return JsonResponse({
        'user': {
            'display_id': profile.display_id,
            'email': request.user.email,
            'full_name': request.user.get_full_name(),
            'role': profile.role,
        },
        'stats': stats
    })

# ---------------------------------------------------------------------------
# SETTINGS (Belongs in Accounts)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_details(request):
    user = request.user
    profile = user.profile
    return Response({
        'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email,
        'dob': profile.dob, 'phone_number': profile.phone_number, 'gender': profile.gender,
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_info(request):
    user = request.user
    profile = user.profile
    data = request.data
    try:
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save()
        profile.phone_number = data.get('phone_number', profile.phone_number)
        profile.gender = data.get('gender', profile.gender)
        if 'dob' in data: profile.dob = data['dob']
        profile.save()
        return Response({'message': 'Profile updated successfully'})
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    if not user.check_password(request.data.get('current_password')):
        return Response({'error': 'Current password is incorrect'}, status=400)
    user.set_password(request.data.get('new_password'))
    user.save()
    return Response({'message': 'Password updated successfully'})