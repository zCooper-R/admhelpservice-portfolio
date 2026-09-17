from django.contrib import auth
from django.contrib.auth.middleware import RemoteUserMiddleware


class HeaderFallbackRemoteUserMiddleware(RemoteUserMiddleware):
    header_candidates = (
        'REMOTE_USER',
        'HTTP_X_REMOTE_USER',
        'HTTP_REMOTE_USER',
    )

    def _get_username(self, request):
        for header in self.header_candidates:
            username = request.META.get(header)
            if username:
                return username
        return None

    def process_request(self, request):
        if not hasattr(request, "user"):
            return super().process_request(request)

        username = self._get_username(request)
        if username is None:
            if self.force_logout_if_no_header and request.user.is_authenticated:
                self._remove_invalid_user(request)
            return

        if request.user.is_authenticated:
            if request.user.get_username() == self.clean_username(username, request):
                return
            self._remove_invalid_user(request)

        user = auth.authenticate(request, remote_user=username)
        if user:
            request.user = user
            auth.login(request, user)

    async def aprocess_request(self, request):
        if not hasattr(request, "user"):
            return await super().aprocess_request(request)

        username = self._get_username(request)
        if username is None:
            if self.force_logout_if_no_header:
                user = await request.auser()
                if user.is_authenticated:
                    await self._aremove_invalid_user(request)
            return

        user = await request.auser()
        if user.is_authenticated:
            if user.get_username() == self.clean_username(username, request):
                return
            await self._aremove_invalid_user(request)

        user = await auth.aauthenticate(request, remote_user=username)
        if user:
            request.user = user
            await auth.alogin(request, user)
