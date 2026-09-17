from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.order_communication.constants import MessageType, MessageVisibility
from apps.order_communication.models import OrderMessage
from apps.order_communication.services.attachments import create_attachments
from apps.order_communication.services.audit import log_message_action, log_thread_created
from apps.order_communication.services.notifications import (
    emit_internal_note_notifications,
    emit_public_message_notifications,
    emit_system_event_notifications,
)
from apps.order_communication.services.policies import (
    can_delete_message,
    can_edit_message,
    can_post_internal_note,
    can_post_public_reply,
)
from apps.order_communication.services.threads import get_or_create_thread, touch_thread
from apps.orders.services.waiting import update_waiting_for_public_reply


def _create_message(*, order, author, body, files=None, message_type=None, visibility=None, event_type="", payload=None):
    with transaction.atomic():
        thread, created = get_or_create_thread(order, actor=author)
        if created:
            log_thread_created(actor=author, thread=thread)

        message = OrderMessage.objects.create(
            thread=thread,
            author=author if getattr(author, "is_authenticated", False) else None,
            message_type=message_type,
            visibility=visibility,
            system_event_type=event_type,
            body=body or "",
            payload=payload or {},
        )
        create_attachments(message, files or [], author)
        touch_thread(thread, message_type=message_type, at=message.created_at)
    return message


def create_public_message(order, author, body, files=None):
    if not can_post_public_reply(author, order):
        raise PermissionDenied("You cannot post a public reply for this ticket.")

    message = _create_message(
        order=order,
        author=author,
        body=body,
        files=files,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
    )
    update_waiting_for_public_reply(order, author, at=message.created_at)
    emit_public_message_notifications(message, author)
    log_message_action(action="order_message.create", actor=author, message=message)
    return message


def create_internal_note(order, author, body, files=None):
    if not can_post_internal_note(author, order):
        raise PermissionDenied("You cannot post an internal note for this ticket.")

    message = _create_message(
        order=order,
        author=author,
        body=body,
        files=files,
        message_type=MessageType.INTERNAL_NOTE,
        visibility=MessageVisibility.STAFF_ONLY,
    )
    emit_internal_note_notifications(message, author)
    log_message_action(action="order_note.create", actor=author, message=message)
    return message


def create_system_event(order, actor, event_type, payload=None, visibility=None, body=""):
    message = _create_message(
        order=order,
        author=actor,
        body=body,
        files=None,
        message_type=MessageType.SYSTEM_EVENT,
        visibility=visibility or MessageVisibility.REQUESTER_AND_STAFF,
        event_type=event_type,
        payload=payload or {},
    )
    emit_system_event_notifications(message, actor)
    log_message_action(action="order_system_event.create", actor=actor, message=message)
    return message


def edit_message(message, actor, body):
    if not can_edit_message(actor, message):
        raise PermissionDenied("You cannot edit this message.")

    message.body = body
    message.edited_by = actor if getattr(actor, "is_authenticated", False) else None
    message.edited_at = timezone.now()
    message.save(update_fields=["body", "edited_by", "edited_at", "updated_at"])
    log_message_action(action="order_message.edit", actor=actor, message=message)
    return message


def soft_delete_message(message, actor, reason=None):
    if not can_delete_message(actor, message):
        raise PermissionDenied("You cannot delete this message.")

    message.is_deleted = True
    message.deleted_by = actor if getattr(actor, "is_authenticated", False) else None
    message.deleted_at = timezone.now()
    message.payload = {**(message.payload or {}), "delete_reason": reason or ""}
    message.save(update_fields=["is_deleted", "deleted_by", "deleted_at", "payload", "updated_at"])
    log_message_action(action="order_message.delete", actor=actor, message=message)
    return message
