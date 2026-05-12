import jwt
import functools
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile
from jwt import PyJWKClient
from django.views.decorators.csrf import csrf_exempt


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

        if not token:
            return JsonResponse({'error': 'Token missing.'}, status=401)

        try:
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get('alg')

            if alg == 'HS256':
                if not settings.SUPABASE_JWT_SECRET:
                    return JsonResponse({'error': 'Server misconfiguration: SUPABASE_JWT_SECRET not set for HS256 token.'}, status=500)
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=['HS256'],
                    options={"verify_aud": False},
                )
            elif alg in ['RS256', 'ES256']:
                import os
                
                db_user = os.environ.get('DB_USER', '')
                if '.' in db_user:
                    project_ref = db_user.split('.')[1]
                else:
                    return JsonResponse({'error': 'Server misconfiguration: Could not determine Supabase project ref.'}, status=500)
                
                jwks_url = f"https://{project_ref}.supabase.co/auth/v1/.well-known/jwks.json"
                jwks_client = PyJWKClient(jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[alg],
                    options={"verify_aud": False},
                )
            else:
                return JsonResponse({'error': f'Unsupported algorithm: {alg}'}, status=401)
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired.'}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'error': f'Invalid token: {str(e)}'}, status=401)
        except Exception as e:
            return JsonResponse({'error': f'Auth error: {str(e)}'}, status=500)

        supabase_uid = payload.get('sub')
        email = payload.get('email', '')
        user_metadata = payload.get('user_metadata', {})

        
        role = user_metadata.get('role', 'patient')
        if role not in ('patient', 'staff', 'admin'):
            role = 'patient'

       
        try:
            profile = UserProfile.objects.select_related('user').get(supabase_uid=supabase_uid)
            django_user = profile.user
        except UserProfile.DoesNotExist:
            
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

        # Final safeguard: Block access if the admin hasn't approved the account yet
        if not profile.is_approved:
            return JsonResponse({
                'error': 'Forbidden. Your account is pending approval by an administrator.'
            }, status=403)

        return view_func(request, *args, **kwargs)

    return csrf_exempt(wrapper)


def role_required(*allowed_roles):
    
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
