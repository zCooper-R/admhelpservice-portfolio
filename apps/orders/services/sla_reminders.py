from urllib.parse import urlencode

from django.core.cache import cache
from django.urls import reverse

from apps.notifications.constants import NotificationEventType
from apps.notifications.services import create_notification
from apps.orders.choices import OrderWaitingFor
from apps.orders.services.sla import get_sla_state

SLA_REMINDER_WARNING_TTL_SECONDS = 12 * 60 * 60
SLA_REMINDER_OVERDUE_TTL_SECONDS = 12 * 60 * 60

SLA_REMINDER_STATES = {"warning", "overdue"}


def get_sla_reminder_recipient(order):
    if getattr(order, "waiting_for", None) == OrderWaitingFor.REQUESTER:
        return getattr(order, "owner", None)

    if getattr(order, "waiting_for", None) != OrderWaitingFor.EXECUTOR:
        return None

    order_object = getattr(order, "content_object", None)
    specialist = getattr(order_object, "support_specialist", None) if order_object is not None else None
    return getattr(specialist, "user", None) if specialist is not None else None


def build_sla_reminder_cache_key(order, recipient, state):
    return f"sla_reminder:{order.id}:{recipient.id}:{state}"


def get_sla_reminder_ttl(state):
    if state == "warning":
        return SLA_REMINDER_WARNING_TTL_SECONDS
    if state == "overdue":
        return SLA_REMINDER_OVERDUE_TTL_SECONDS
    return 0


def should_send_sla_reminder(order, recipient, state):
    if recipient is None or state not in SLA_REMINDER_STATES:
        return False
    return cache.add(
        build_sla_reminder_cache_key(order, recipient, state),
        1,
        timeout=get_sla_reminder_ttl(state),
    )


def send_sla_reminder(order, recipient, state):
    title, body = _build_sla_reminder_message(order, state)
    return create_notification(
        recipient=recipient,
        title=title,
        body=body,
        event_type=NotificationEventType.ORDER_SLA_REMINDER,
        target_object=order,
        target_url=_build_sla_target_url(order),
        metadata={
            "order_id": order.id,
            "waiting_for": order.waiting_for,
            "sla_state": state,
            "reminder_kind": "response_sla",
        },
    )


def process_order_sla_reminder(order):
    state = get_sla_state(order)
    if state not in SLA_REMINDER_STATES:
        return None

    recipient = get_sla_reminder_recipient(order)
    if not should_send_sla_reminder(order, recipient, state):
        return None

    return send_sla_reminder(order, recipient, state)


def _build_sla_reminder_message(order, state):
    order_ref = f"№{order.pk}"
    title = f"Требуется ваш ответ по заявке {order_ref}"
    if state == "warning":
        body = f"По заявке {order_ref} ожидается ваш ответ. Срок ответа подходит к концу."
    else:
        body = f"По заявке {order_ref} ожидается ваш ответ. Срок ответа уже просрочен."
    return title, body


def _build_sla_target_url(order):
    base_url = reverse("orders:orders_list") if order.waiting_for == OrderWaitingFor.REQUESTER else reverse("orders:tasks_list")
    return f"{base_url}?{urlencode({'modal': order.get_absolute_url()})}"
