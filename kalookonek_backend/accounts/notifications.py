import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_push_notification(user, message):
    """Stub function for sending push notifications"""
    logger.info(f"[PUSH DISPATCH] To {user.username}: {message}")
    print(f"[PUSH DISPATCH] To {user.username}: {message}")
