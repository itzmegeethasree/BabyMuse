from django.contrib.auth import get_user_model
from social_core.exceptions import AuthException

User = get_user_model()

def handle_existing_email(strategy, details, backend, uid, user=None, *args, **kwargs):
    email = details.get('email')
    if email:
        try:
            existing_user = User.objects.get(email=email)
            return {'user': existing_user}
        except User.DoesNotExist:
            return
    else:
        raise AuthException(backend, "No email provided by Google.")


def block_check(strategy, details, user=None, *args, **kwargs):
    if user and hasattr(user, 'is_blocked') and user.is_blocked:
        raise AuthException(strategy.backend, "Your account has been blocked by admin.")