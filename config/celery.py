import os
import logging
from celery import Celery

import utils.logging_celery  # noqa: F401
from settings_loader import resolve_settings_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", resolve_settings_module())

app = Celery('admHelpService.config')
app.config_from_object('django.conf:settings', namespace="CELERY")
app.autodiscover_tasks()
logger = logging.getLogger('adm.celery')


@app.task(bind=True)
def debug_task(self):
    logger.debug('celery debug task request=%r', self.request, extra={'event': 'celery_debug_task'})
