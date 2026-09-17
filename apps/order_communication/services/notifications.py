from urllib.parse import urlencode

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.urls import reverse

from apps.notifications.constants import NotificationEventType
from apps.notifications.models import Notification
from apps.notifications.policies import MODERATOR_AUDIENCE, REQUESTER_AUDIENCE, SPECIALIST_AUDIENCE
from apps.notifications.services import NotificationPayload, create_notifications
from apps.order_communication.constants import MessageType
from apps.order_communication.services.policies import can_view_message, is_requester, is_staff_actor
from apps.orders.services.workflow import get_moderators_for_order


DISCUSSION_NOTIFICATION_EVENT = NotificationEventType.ORDER_COMMENT_ADDED


def _build_modal_target_url(order, audience, *, message=None):
    modal_url = order.get_absolute_url()
    base_url = reverse("orders:orders_list") if audience == REQUESTER_AUDIENCE else reverse("orders:tasks_list")
    query = {
        "modal": modal_url,
        "modal_tab": "discussion",
    }
    if message is not None:
        query["modal_message"] = str(message.pk)
    return f"{base_url}?{urlencode(query)}"


def _get_actor_label(actor) -> str:
    if actor is None:
        return "Система"
    full_name = getattr(actor, "full_name", "") or ""
    return full_name.strip() or getattr(actor, "username", "") or str(actor)


def _truncate_preview(text: str, limit: int = 90) -> str:
    value = " ".join((text or "").split())
    if not value:
        return "Без текста"
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}…"


def _build_notification_metadata(message):
    return {
        "order_id": message.thread.order_id,
        "thread_id": message.thread_id,
        "message_id": message.pk,
        "message_type": message.message_type,
        "visibility": message.visibility,
    }


def _notification_exists(*, recipient, message, event_type):
    order_ct = ContentType.objects.get_for_model(message.thread.order, for_concrete_model=False)
    return Notification.objects.filter(
        recipient=recipient,
        event_type=event_type,
        target_content_type=order_ct,
        target_object_id=message.thread.order_id,
        metadata__message_id=message.pk,
    ).exists()


def _build_payload(*, recipient, audience, message, title, body):
    return NotificationPayload(
        recipient=recipient,
        title=title,
        body=body,
        event_type=DISCUSSION_NOTIFICATION_EVENT,
        actor=message.author,
        target_object=message.thread.order,
        target_url=_build_modal_target_url(message.thread.order, audience, message=message),
        metadata=_build_notification_metadata(message),
    )


def _get_staff_recipients(message, *, include_specialist=True):
    order = message.thread.order
    order_object = getattr(order, "content_object", None)
    recipients = {}

    specialist = getattr(order_object, "support_specialist", None) if order_object is not None else None
    specialist_user = getattr(specialist, "user", None) if specialist is not None else None
    if include_specialist and specialist_user is not None:
        recipients[specialist_user.pk] = (specialist_user, SPECIALIST_AUDIENCE)

    for moderator in get_moderators_for_order(order_object) if order_object is not None else []:
        recipients[moderator.pk] = (moderator, MODERATOR_AUDIENCE)

    User = apps.get_model("users", "User")
    for superuser in User.objects.filter(is_active=True, is_superuser=True):
        recipients[superuser.pk] = (superuser, MODERATOR_AUDIENCE)

    filtered = []
    for recipient, audience in recipients.values():
        if recipient == message.author:
            continue
        if not can_view_message(recipient, message):
            continue
        filtered.append((recipient, audience))
    return filtered


def _create_discussion_notifications(payloads, *, message):
    unique_payloads = []
    seen_recipient_ids = set()
    for payload in payloads:
        recipient_id = getattr(payload.recipient, "pk", None)
        if recipient_id is None or recipient_id in seen_recipient_ids:
            continue
        seen_recipient_ids.add(recipient_id)
        if _notification_exists(recipient=payload.recipient, message=message, event_type=payload.event_type):
            continue
        unique_payloads.append(payload)

    if not unique_payloads:
        return []

    transaction.on_commit(lambda: create_notifications(unique_payloads))
    return unique_payloads


def emit_public_message_notifications(message, actor):
    order = message.thread.order
    order_object = getattr(order, "content_object", None)
    order_ref = f"№{order.pk}"
    actor_label = _get_actor_label(actor)
    preview = _truncate_preview(message.body)
    title = f"Новый ответ по заявке {order_ref}"
    body = f"{actor_label}: {preview}"

    payloads = []
    if is_requester(actor, order):
        for recipient, audience in _get_staff_recipients(message):
            payloads.append(
                _build_payload(
                    recipient=recipient,
                    audience=audience,
                    message=message,
                    title=title,
                    body=body,
                )
            )
    elif order_object is not None and is_staff_actor(actor, order):
        requester = getattr(order, "owner", None)
        if requester is not None and requester != actor and can_view_message(requester, message):
            payloads.append(
                _build_payload(
                    recipient=requester,
                    audience=REQUESTER_AUDIENCE,
                    message=message,
                    title=title,
                    body=body,
                )
            )

    return _create_discussion_notifications(payloads, message=message)


def emit_internal_note_notifications(message, actor):
    order = message.thread.order
    order_ref = f"№{order.pk}"
    actor_label = _get_actor_label(actor)
    preview = _truncate_preview(message.body)
    title = f"Новая внутренняя заметка по заявке {order_ref}"
    body = f"{actor_label}: {preview}"

    payloads = [
        _build_payload(
            recipient=recipient,
            audience=audience,
            message=message,
            title=title,
            body=body,
        )
        for recipient, audience in _get_staff_recipients(message)
    ]
    return _create_discussion_notifications(payloads, message=message)


def emit_system_event_notifications(message, actor):
    return []
