import jwt
import functools
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile


def supabase_auth_required(view_func):
    """
    Decorator that protects API views by validating Supabase JWTs.

    Flow:
    1. Extracts the Bearer token from the Authorization header.
    2. Decodes it using the SUPABASE_JWT_SECRET.
    3. Auto-syncs: creates a Django User + UserProfile if one doesn't exist yet.
    4. Attaches request.user so downstream views work normally.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header missing or malformed.'}, status=401)

        token = auth_header.split(' ', 1)[1]

        if not settings.SUPABASE_JWT_SECRET:
            return JsonResponse({'error': 'Server misconfiguration: JWT secret not set.'}, status=500)

        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                options={"verify_aud": False},  # Supabase sets audience to 'authenticated'
            )
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired.'}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'error': f'Invalid token: {str(e)}'}, status=401)

        supabase_uid = payload.get('sub')
        email = payload.get('email', '')
        user_metadata = payload.get('user_metadata', {})

        # Determine role from Supabase user metadata (defaults to 'patient')
        role = user_metadata.get('role', 'patient')
        if role not in ('patient', 'staff', 'admin'):
            role = 'patient'

        # Auto-sync: find existing profile or create a new Django User + UserProfile
        try:
            profile = UserProfile.objects.select_related('user').get(supabase_uid=supabase_uid)
            django_user = profile.user
        except UserProfile.DoesNotExist:
            # First time this Supabase user is hitting the API — create their Django record
            django_user, _ = User.objects.get_or_create(
                username=email,
                defaults={'email': email}
            )
            profile = UserProfile.objects.create(
                user=django_user,
                supabase_uid=supabase_uid,
                role=role,
            )

        request.user = django_user
        request.user_profile = profile
        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """
    Decorator that enforces role-based access control.
    Must be used on views that are already wrapped with @supabase_auth_required,
    or it wraps them automatically.

    Usage:
        @role_required('staff', 'admin')
        def my_staff_view(request):
            ...
    """
    def decorator(view_func):
        @supabase_auth_required
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user_profile.role not in allowed_roles:
                return JsonResponse(
                    {'error': 'Forbidden. Insufficient role permissions.'},
                    status=403
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
