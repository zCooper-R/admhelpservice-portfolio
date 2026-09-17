import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from utils.logging_audit import log_audit


security_logger = logging.getLogger('adm.security')


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    security_logger.info(
        'user logged in user_id=%s username=%s',
        user.pk,
        user.get_username(),
        extra={'event': 'auth_login_success'},
    )
    log_audit(
        action='auth.login',
        actor=user,
        entity='auth.user',
        entity_id=user.pk,
    )


@receiver(user_logged_out)
def handle_user_logged_out(sender, request, user, **kwargs):
    user_id = getattr(user, 'pk', '-')
    username = user.get_username() if user else 'anonymous'
    security_logger.info(
        'user logged out user_id=%s username=%s',
        user_id,
        username,
        extra={'event': 'auth_logout'},
    )
    if user:
        log_audit(
            action='auth.logout',
            actor=user,
            entity='auth.user',
            entity_id=user.pk,
        )


@receiver(user_login_failed)
def handle_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username') if isinstance(credentials, dict) else 'unknown'
    security_logger.warning(
        'login failed username=%s',
        username or 'unknown',
        extra={'event': 'auth_login_failed'},
    )
