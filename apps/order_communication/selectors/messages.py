from apps.order_communication.constants import MessageVisibility
from apps.order_communication.models import OrderMessage
from apps.order_communication.services.policies import can_view_thread, is_staff_actor


def get_visible_messages_for_thread(thread, user):
    if not can_view_thread(user, thread.order):
        return OrderMessage.objects.none()

    queryset = (
        OrderMessage.objects.select_related("author", "edited_by", "deleted_by", "thread", "thread__order")
        .prefetch_related("attachments")
        .filter(thread=thread)
        .order_by("created_at", "id")
    )
    if is_staff_actor(user, thread.order):
        return queryset
    return queryset.filter(visibility=MessageVisibility.REQUESTER_AND_STAFF)


def get_timeline_page(thread, user, *, before_id=None, limit=50):
    queryset = get_visible_messages_for_thread(thread, user)
    if before_id is not None:
        queryset = queryset.filter(id__lt=before_id)
    return queryset.order_by("-created_at", "-id")[:limit]
