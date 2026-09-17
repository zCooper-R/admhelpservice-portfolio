import logging

from celery import shared_task

from apps.orders.choices import OrderWaitingFor
from apps.orders.models.base import Order
from apps.orders.services.sla_reminders import process_order_sla_reminder
from apps.orders.utils.datatables import prefetch_order_content_objects

logger = logging.getLogger("adm.apps.orders")


@shared_task
def task_process_sla_reminders(_request_id: str = None):
    orders = list(
        Order.objects.select_related("owner", "content_type").filter(
            waiting_for__in=[OrderWaitingFor.EXECUTOR, OrderWaitingFor.REQUESTER],
            waiting_since__isnull=False,
        )
    )
    prefetch_order_content_objects(orders)

    sent_count = 0
    for order in orders:
        try:
            if process_order_sla_reminder(order) is not None:
                sent_count += 1
        except Exception:
            logger.exception(
                "sla reminder processing failed order_id=%s",
                order.id,
                extra={"event": "sla_reminder_processing_failed", "order_id": order.id},
            )
    return sent_count
