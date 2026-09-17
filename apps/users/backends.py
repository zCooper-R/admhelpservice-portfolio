import logging

from django_remote_auth_ldap.backend import RemoteUserLDAPBackend


logger = logging.getLogger('adm.security')


class myBackend(RemoteUserLDAPBackend):
    def authenticate(self, request, remote_user=None):
        logger.info(
            'remote auth attempt remote_user=%s',
            remote_user or 'unknown',
            extra={'event': 'auth_remote_attempt'},
        )
        user = super().authenticate(request, remote_user)
        if user is None:
            logger.warning(
                'remote auth failed remote_user=%s',
                remote_user or 'unknown',
                extra={'event': 'auth_remote_failed'},
            )
        return user
