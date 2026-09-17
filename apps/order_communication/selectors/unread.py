from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.order_communication.constants import MessageVisibility
from apps.order_communication.models import OrderMessage, OrderThread, OrderThreadReadState
from apps.order_communication.services.policies import can_view_thread, is_staff_actor


def get_unread_threads_for_user(user):
    return OrderThreadReadState.objects.filter(user=user).exclude(unread_count_hint=0)


def get_visible_unread_messages_queryset(thread, user):
    if thread is None or not can_view_thread(user, thread.order):
        return OrderMessage.objects.none()

    queryset = OrderMessage.objects.filter(thread=thread, is_deleted=False).exclude(author=user)
    if not is_staff_actor(user, thread.order):
        queryset = queryset.filter(visibility=MessageVisibility.REQUESTER_AND_STAFF)

    read_state = (
        OrderThreadReadState.objects.filter(thread=thread, user=user)
        .only("last_read_message_id")
        .first()
    )
    if read_state and read_state.last_read_message_id:
        queryset = queryset.filter(id__gt=read_state.last_read_message_id)
    return queryset


def get_unread_count_by_order_ids(order_ids, user):
    if not order_ids:
        return {}

    read_state_last_message = Subquery(
        OrderThreadReadState.objects.filter(thread=OuterRef("pk"), user=user)
        .values("last_read_message_id")[:1],
        output_field=IntegerField(),
    )

    visibility_filter = Q()
    if not user.is_superuser:
        threads = OrderThread.objects.filter(order_id__in=order_ids).select_related("order", "order__owner", "order__content_type")
        staff_order_ids = {thread.order_id for thread in threads if is_staff_actor(user, thread.order)}
        requester_order_ids = set(order_ids) - staff_order_ids

        visibility_filter = Q()
        if staff_order_ids:
            visibility_filter |= Q(order_id__in=staff_order_ids)
        if requester_order_ids:
            visibility_filter |= Q(order_id__in=requester_order_ids, messages__visibility=MessageVisibility.REQUESTER_AND_STAFF)

        thread_queryset = threads
    else:
        thread_queryset = OrderThread.objects.filter(order_id__in=order_ids)
    if not user.is_superuser and not visibility_filter:
        return {}

    counts = (
        thread_queryset
        .annotate(user_last_read_message_id=Coalesce(read_state_last_message, Value(0)))
        .annotate(
            unread_messages=Count(
                "messages",
                filter=(
                    Q(messages__is_deleted=False)
                    & ~Q(messages__author=user)
                    & Q(messages__id__gt=F("user_last_read_message_id"))
                    & visibility_filter
                ),
            )
        )
        .values_list("order_id", "unread_messages")
    )
    return {order_id: unread_count for order_id, unread_count in counts}


def get_global_unread_thread_count(user):
    return get_unread_threads_for_user(user).count()
