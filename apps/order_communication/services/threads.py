from django.db import transaction
from django.utils import timezone

from apps.order_communication.constants import MessageType
from apps.order_communication.models import OrderThread


def get_thread_for_order(order):
    return (
        OrderThread.objects.select_related("order", "order__owner", "created_by")
        .filter(order=order)
        .first()
    )


def get_or_create_thread(order, actor=None):
    with transaction.atomic():
        thread, created = OrderThread.objects.get_or_create(
            order=order,
            defaults={"created_by": actor if getattr(actor, "is_authenticated", False) else None},
        )
    return thread, created


def ensure_thread_for_wrapper_order(order, actor=None):
    thread, _ = get_or_create_thread(order, actor=actor)
    return thread


def touch_thread(thread, *, message_type=None, at=None):
    timestamp = at or timezone.now()
    update_fields = ["updated_at", "last_message_at"]
    thread.last_message_at = timestamp

    if message_type == MessageType.PUBLIC_REPLY:
        thread.last_public_message_at = timestamp
        update_fields.append("last_public_message_at")
    elif message_type == MessageType.INTERNAL_NOTE:
        thread.last_internal_note_at = timestamp
        update_fields.append("last_internal_note_at")

    thread.save(update_fields=update_fields)
