import contextvars
import uuid


request_id_var = contextvars.ContextVar('request_id', default='-')
user_id_var = contextvars.ContextVar('user_id', default='-')
username_var = contextvars.ContextVar('username', default='anonymous')
remote_addr_var = contextvars.ContextVar('remote_addr', default='-')
path_var = contextvars.ContextVar('path', default='-')
method_var = contextvars.ContextVar('method', default='-')
celery_task_id_var = contextvars.ContextVar('celery_task_id', default='-')


def generate_request_id() -> str:
    return uuid.uuid4().hex


def set_log_context(**kwargs):
    tokens = {}
    for key, value in kwargs.items():
        var = _CONTEXT_VARS.get(key)
        if var is None:
            continue
        tokens[key] = var.set(value if value not in (None, '') else '-')
    return tokens


def reset_log_context(tokens):
    for key, token in tokens.items():
        var = _CONTEXT_VARS.get(key)
        if var is not None:
            var.reset(token)


def get_log_context() -> dict:
    return {
        'request_id': request_id_var.get(),
        'user_id': user_id_var.get(),
        'username': username_var.get(),
        'remote_addr': remote_addr_var.get(),
        'path': path_var.get(),
        'method': method_var.get(),
        'celery_task_id': celery_task_id_var.get(),
    }


def bind_request_context(request, request_id: str):
    user = getattr(request, 'user', None)
    is_authenticated = bool(user and getattr(user, 'is_authenticated', False))
    username = getattr(user, 'get_username', lambda: None)() if is_authenticated else None
    user_id = getattr(user, 'pk', None) if is_authenticated else None
    return set_log_context(
        request_id=request_id,
        user_id=user_id,
        username=username,
        remote_addr=get_client_ip(request),
        path=getattr(request, 'path', '-'),
        method=getattr(request, 'method', '-'),
    )


def bind_celery_context(task_id: str, request_id: str = None):
    return set_log_context(
        celery_task_id=task_id,
        request_id=request_id or task_id,
    )


def get_client_ip(request) -> str:
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '-')


_CONTEXT_VARS = {
    'request_id': request_id_var,
    'user_id': user_id_var,
    'username': username_var,
    'remote_addr': remote_addr_var,
    'path': path_var,
    'method': method_var,
    'celery_task_id': celery_task_id_var,
}
