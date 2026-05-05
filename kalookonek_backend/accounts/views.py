from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import authenticate
from .models import UserProfile, Appointment

# ---------------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------------


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Handles DRF Token Authentication login.
    Satisfies the 'login' attribute requirement in urls.py.
    """
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        profile = get_object_or_404(UserProfile, user=user)
        return Response({
            'token': token.key,
            'role': profile.role,
            'user_id': user.id,
            'display_id': profile.display_id
        })
    else:
        return Response({'error': 'Invalid Credentials'}, status=401)

# ---------------------------------------------------------------------------
# PROFILE & DASHBOARD STATS
# ---------------------------------------------------------------------------


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    stats = {
        # Count only patients aged 60 or older
        'seniors': UserProfile.objects.filter(role='patient', age__gte=60).count(),
        'pending': UserProfile.objects.filter(role='staff', is_approved=False).count(),
        'appointments': Appointment.objects.count(),
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

    return Response({
        'user': {
            'display_id': profile.display_id,
            'email': request.user.email,
            'full_name': request.user.get_full_name() or request.user.username,
            'role': profile.role,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        },
        'stats': stats,
        'applicants': applicants_list
    })

# ---------------------------------------------------------------------------
# PATIENT MANAGEMENT
# ---------------------------------------------------------------------------


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_patients(request):
    search_query = request.query_params.get('search', '').strip()
    barangay_filter = request.query_params.get('barangay', '').strip()
    status_filter = request.query_params.get('status', '').strip()

    patients_qs = UserProfile.objects.filter(role='patient')

    if search_query:
        patients_qs = patients_qs.filter(
            Q(display_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    if barangay_filter and barangay_filter != "All Barangays":
        patients_qs = patients_qs.filter(barangay=barangay_filter)

    if status_filter == "COMPLETED":
        patients_qs = patients_qs.filter(updated_at__isnull=False)
    elif status_filter == "PENDING":
        patients_qs = patients_qs.filter(updated_at__isnull=True)

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

    return Response(patients_list)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_patients(request):
    search_query = request.query_params.get('search', '').strip()
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

    return Response(patients_list)

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def account_settings(request):
    data = request.data
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)

    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'phone_number' in data:
        profile.phone_number = data['phone_number']

    user.save()
    profile.save()

    return Response({
        'message': 'Profile updated successfully.',
        'display_id': profile.display_id
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointments(request):
    # For now, let's just get all appointments
    appointments = Appointment.objects.all().order_by('start_time')

    data = []
    for appt in appointments:
        data.append({
            'id': appt.id,
            'patient_name': appt.patient_name,
            'display_id': appt.patient_id_display,
            'time': appt.start_time.strftime('%I:%M %p'),
            'end_time': appt.end_time.strftime('%I:%M %p'),
            'purpose': appt.details,
            'status': appt.status
        })
    return Response(data)
