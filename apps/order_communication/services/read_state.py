from django.utils import timezone

from apps.order_communication.models import OrderThreadReadState
from apps.order_communication.selectors.messages import get_visible_messages_for_thread
from apps.order_communication.selectors.unread import get_visible_unread_messages_queryset
from apps.order_communication.services.audit import log_thread_read


def get_or_create_read_state(thread, user):
    return OrderThreadReadState.objects.get_or_create(thread=thread, user=user)


def mark_thread_read(thread, user, up_to_message=None):
    read_state, _ = get_or_create_read_state(thread, user)
    last_message = up_to_message
    if last_message is None:
        last_message = get_visible_messages_for_thread(thread, user).order_by("-created_at", "-id").first()

    read_state.last_read_at = timezone.now()
    if last_message is not None:
        read_state.last_read_message = last_message
    read_state.unread_count_hint = 0
    read_state.save(update_fields=["last_read_message", "last_read_at", "unread_count_hint", "updated_at"])
    log_thread_read(actor=user, thread=thread, read_state=read_state)
    return read_state


def get_thread_unread_count(thread, user):
    if thread is None:
        return 0
    return get_visible_unread_messages_queryset(thread, user).count()


def get_first_unread_message_id(thread, user):
    if thread is None:
        return None
    return (
        get_visible_unread_messages_queryset(thread, user)
        .order_by("created_at", "id")
        .values_list("id", flat=True)
        .first()
    )


def get_unread_summary_for_user(user):
    unread_threads = (
        OrderThreadReadState.objects.filter(user=user)
        .exclude(unread_count_hint=0)
        .count()
    )
    return {"unread_threads": unread_threads}
