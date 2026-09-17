from utils.logging_middleware import RequestContextMiddleware


class RequestTimeMiddleware(RequestContextMiddleware):
    """Backward-compatible alias for the central request logging middleware."""


class RequestLoggerMiddleware(RequestContextMiddleware):
    """Backward-compatible alias for the central request logging middleware."""
