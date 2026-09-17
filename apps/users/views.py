import logging

from django.contrib.auth.views import LoginView, LogoutView


logger = logging.getLogger('adm.security')


class myLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        logger.warning(
            'interactive login rejected username=%s',
            form.data.get('username') or 'unknown',
            extra={'event': 'auth_login_invalid_form'},
        )
        return super().form_invalid(form)


class myLogoutView(LogoutView):
    ...
