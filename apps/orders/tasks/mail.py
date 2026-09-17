import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from apps.orders.models.feedback import Feedback
from apps.orders.services.mailbox import process_done_order_printer_fill_emails
from apps.orders.services.notifications import OrderNotificationService
from config.celery import app


logger = logging.getLogger(__name__)


@app.task
def task_process_done_order_printer_fill_emails(_request_id: str = None):
    process_done_order_printer_fill_emails()


@shared_task(
    autoretry_for=(ObjectDoesNotExist,),
    retry_backoff=5,
    max_retries=5,
    acks_late=True,
)
def task_mail_admins_feedback(feedback_id, _request_id: str = None) -> None:
    try:
        logger.info('feedback mail notification started feedback_id=%s', feedback_id, extra={'event': 'mail_feedback_started'})
        OrderNotificationService.mail_admins_feedback(feedback_id)
    except Feedback.DoesNotExist:
        logger.warning('feedback mail notification skipped feedback_id=%s reason=not_found', feedback_id)


@shared_task(
    autoretry_for=(ObjectDoesNotExist,),
    retry_backoff=5,
    max_retries=5,
    acks_late=True,
)
def task_mail_admins(
    order_id: int,
    subject: str = None,
    context: dict = None,
    template: str = None,
    _request_id: str = None,
) -> None:
    logger.info('admin mail task started order_id=%s', order_id, extra={'event': 'mail_admins_started'})
    OrderNotificationService.mail_admins_for_order(order_id, subject, context, template)


@shared_task
def task_mail_organisation(
    order_printer_id: int,
    subject: str = None,
    context: dict = None,
    template: str = None,
    _request_id: str = None,
) -> None:
    OrderNotificationService.mail_organisation_printer(order_printer_id, subject, context, template)


@shared_task
def task_mail_organisation_from_admin_panel(
    order_printer_id: int,
    subject: str = None,
    context: dict = None,
    template: str = None,
    _request_id: str = None,
) -> None:
    OrderNotificationService.mail_organisation_from_admin_panel(order_printer_id, subject, context, template)


@shared_task
def task_mail_protection_sector(
    order_account_id: int,
    subject: str = None,
    context: dict = None,
    template: str = None,
    _request_id: str = None,
) -> None:
    OrderNotificationService.mail_protection_sector(order_account_id, subject, context, template)
