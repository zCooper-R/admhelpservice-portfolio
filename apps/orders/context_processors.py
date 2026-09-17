import apps
from django.conf import settings

from apps.orders.services.workflow import user_can_access_task_queue


def base_context_processor(request):
    return {
        'BASE_URL': request.build_absolute_uri("/").rstrip("/"),
        'TELEGRAM_BOT_URL': settings.TELEGRAM_BOT_LINK,
        'SITE_NAME': settings.SITE_NAME,
        'VERSION': apps.__version__,
        'orders_can_access_tasks': user_can_access_task_queue(getattr(request, "user", None)),
    }
