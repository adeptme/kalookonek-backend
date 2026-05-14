from rest_framework_simplejwt.authentication import JWTAuthentication


class SupabaseJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        from django.contrib.auth.models import User

        user_id = validated_token.get('sub')
        email = validated_token.get('email')

        # Use update_or_create to keep the email/name in sync with Supabase
        user, created = User.objects.update_or_create(
            username=user_id,
            defaults={
                'email': email,
                # Safe access to metadata in case it's missing
                'first_name': validated_token.get('user_metadata', {}).get('full_name', '')[:30]
            }
        )
        return user
