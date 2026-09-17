import logging
import time

from django.conf import settings

from utils.logging_context import bind_request_context, generate_request_id, reset_log_context


request_logger = logging.getLogger('adm.requests')
security_logger = logging.getLogger('adm.security')
performance_logger = logging.getLogger('adm.performance')


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(settings.REQUEST_ID_HEADER, '') or generate_request_id()
        request.request_id = request_id
        started_at = time.monotonic()
        tokens = bind_request_context(request, request_id)
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            status_code = getattr(response, 'status_code', 500)

            log_extra = {
                'request_id': request_id,
                'status_code': status_code,
                'duration_ms': duration_ms,
                'event': 'http_request',
            }
            if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
                log_extra['user_id'] = request.user.pk
                log_extra['username'] = request.user.get_username()

            request_logger.info(
                'request completed method=%s path=%s status=%s duration_ms=%s',
                request.method,
                request.path,
                status_code,
                duration_ms,
                extra=log_extra,
            )

            if status_code in {401, 403}:
                security_logger.warning(
                    'access denied method=%s path=%s status=%s',
                    request.method,
                    request.path,
                    status_code,
                    extra=log_extra,
                )

            if duration_ms >= settings.SLOW_REQUEST_THRESHOLD_MS:
                performance_logger.warning(
                    'slow request method=%s path=%s status=%s duration_ms=%s',
                    request.method,
                    request.path,
                    status_code,
                    duration_ms,
                    extra=log_extra,
                )

            reset_log_context(tokens)
