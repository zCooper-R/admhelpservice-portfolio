import logging
import time

from celery import signals

from utils.logging_context import bind_celery_context, reset_log_context


celery_logger = logging.getLogger('adm.celery')
performance_logger = logging.getLogger('adm.performance')

_TASK_STATE = {}


@signals.task_prerun.connect
def task_prerun_handler(task_id=None, task=None, args=None, kwargs=None, **_kwargs):
    request_id = None
    if isinstance(kwargs, dict):
        request_id = kwargs.get('_request_id')
    tokens = bind_celery_context(task_id=task_id, request_id=request_id)
    _TASK_STATE[task_id] = {
        'started_at': time.monotonic(),
        'tokens': tokens,
        'task_name': getattr(task, 'name', 'unknown'),
    }
    celery_logger.info(
        'task started name=%s task_id=%s',
        getattr(task, 'name', 'unknown'),
        task_id,
        extra={'event': 'celery_task_started'},
    )


@signals.task_postrun.connect
def task_postrun_handler(task_id=None, task=None, retval=None, state=None, **_kwargs):
    task_state = _TASK_STATE.pop(task_id, {})
    duration_ms = int((time.monotonic() - task_state.get('started_at', time.monotonic())) * 1000)
    celery_logger.info(
        'task finished name=%s task_id=%s state=%s duration_ms=%s',
        getattr(task, 'name', 'unknown'),
        task_id,
        state,
        duration_ms,
        extra={'event': 'celery_task_finished', 'duration_ms': duration_ms},
    )
    if duration_ms >= 3000:
        performance_logger.warning(
            'slow task name=%s task_id=%s state=%s duration_ms=%s',
            getattr(task, 'name', 'unknown'),
            task_id,
            state,
            duration_ms,
            extra={'event': 'celery_task_slow', 'duration_ms': duration_ms},
        )
    tokens = task_state.get('tokens')
    if tokens:
        reset_log_context(tokens)


@signals.task_failure.connect
def task_failure_handler(task_id=None, exception=None, sender=None, einfo=None, **_kwargs):
    celery_logger.error(
        'task failed name=%s task_id=%s error=%s',
        getattr(sender, 'name', 'unknown'),
        task_id,
        exception,
        exc_info=(type(exception), exception, getattr(einfo, 'tb', None)) if exception else None,
        extra={'event': 'celery_task_failed'},
    )


@signals.task_retry.connect
def task_retry_handler(request=None, reason=None, einfo=None, **_kwargs):
    celery_logger.warning(
        'task retry name=%s task_id=%s reason=%s',
        getattr(request, 'task', 'unknown'),
        getattr(request, 'id', '-'),
        reason,
        extra={'event': 'celery_task_retry'},
    )
