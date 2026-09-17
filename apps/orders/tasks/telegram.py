from celery import shared_task

from apps.users import services as user_services
from apps.orders.services.notifications import OrderNotificationService


@shared_task
def task_send_order_object_telegram(object_id: int, content_type_model: str, to=None, _request_id: str = None):
    if to:
        user_services.send_order_object_telegram(
            object_id=object_id,
            content_type_model=content_type_model,
            tlg_ids=to,
        )
        return
    OrderNotificationService.telegram_workflow_moderators(object_id, content_type_model)


@shared_task
def task_telegram_printer_moderators(order_printer_id: int, _request_id: str = None) -> None:
    OrderNotificationService.telegram_workflow_moderators(order_printer_id, "orderprinter")


@shared_task
def task_telegram_transport_moderators(order_transport_id: int, _request_id: str = None) -> None:
    OrderNotificationService.telegram_workflow_moderators(order_transport_id, "ordertransport")


@shared_task
def task_telegram_pc_moderators(order_pc_id: int, _request_id: str = None) -> None:
    OrderNotificationService.telegram_workflow_moderators(order_pc_id, "orderpc")


@shared_task
def task_telegram_aho_moderators(order_aho_id: int, _request_id: str = None) -> None:
    OrderNotificationService.telegram_workflow_moderators(order_aho_id, "orderaho")


@shared_task
def task_telegram_account_moderators(order_account_id: int, _request_id: str = None) -> None:
    OrderNotificationService.telegram_workflow_moderators(order_account_id, "orderaccount")


@shared_task
def task_notification_user(transport_id: int, _request_id: str = None) -> None:
    OrderNotificationService.notify_transport_user(transport_id)


@shared_task
def task_notify_specialist(object_id, content_type_model: str, _request_id: str = None) -> None:
    OrderNotificationService.notify_specialist(object_id, content_type_model)
