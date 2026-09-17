from apps.order_communication.models import OrderThread
from apps.order_communication.services.policies import can_view_thread


def get_thread_for_order_visible_to_user(order, user):
    if not can_view_thread(user, order):
        return None
    return (
        OrderThread.objects.select_related("order", "order__owner", "created_by")
        .prefetch_related("messages__attachments", "messages__author")
        .filter(order=order)
        .first()
    )


def get_thread_with_messages(order, user, *, limit=None, after_id=None):
    thread = get_thread_for_order_visible_to_user(order, user)
    if thread is None:
        return None

    messages_qs = thread.messages.select_related("author", "edited_by", "deleted_by").prefetch_related("attachments")
    if after_id is not None:
        messages_qs = messages_qs.filter(id__gt=after_id)
    if limit is not None:
        messages_qs = messages_qs[:limit]
    thread.visible_messages = list(messages_qs)
    return thread


def get_thread_summary_for_orders(order_ids, user):
    # TODO: extend with unread counts and last activity annotation for ticket list rows.
    return (
        OrderThread.objects.select_related("order")
        .filter(order_id__in=order_ids, order__owner=user)
        .only("id", "order_id", "last_message_at", "last_public_message_at", "last_internal_note_at")
    )
