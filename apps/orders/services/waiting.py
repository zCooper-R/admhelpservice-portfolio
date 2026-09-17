from django.contrib.contenttypes.models import ContentType

from apps.order_communication.services.policies import is_requester, is_staff_actor
from apps.orders.choices import OrderStatus, OrderWaitingFor
from apps.orders.models.base import Order

TERMINAL_ORDER_STATUSES = {
    OrderStatus.DONE,
    OrderStatus.CLOSED,
    OrderStatus.CANCELED,
}


def get_wrapper_order_for_object(order_object):
    return (
        Order.objects.filter(
            content_type=ContentType.objects.get_for_model(order_object, for_concrete_model=False),
            object_id=order_object.pk,
        )
        .first()
    )


def set_waiting_state(order, *, waiting_for, at=None):
    waiting_since = None if waiting_for == OrderWaitingFor.NONE else at
    update_fields = []

    if order.waiting_for != waiting_for:
        order.waiting_for = waiting_for
        update_fields.append("waiting_for")

    if order.waiting_since != waiting_since:
        order.waiting_since = waiting_since
        update_fields.append("waiting_since")

    if update_fields:
        update_fields.append("updated_at")
        order.save(update_fields=update_fields)

    return order


def update_waiting_for_public_reply(order, author, *, at=None):
    current_status = getattr(getattr(order, "content_object", None), "status", None)
    if current_status in TERMINAL_ORDER_STATUSES:
        waiting_for = OrderWaitingFor.NONE
    elif is_requester(author, order):
        waiting_for = OrderWaitingFor.EXECUTOR
    elif is_staff_actor(author, order):
        waiting_for = OrderWaitingFor.REQUESTER
    else:
        waiting_for = OrderWaitingFor.NONE

    return set_waiting_state(order, waiting_for=waiting_for, at=at)


def reset_waiting_for_order(order):
    return set_waiting_state(order, waiting_for=OrderWaitingFor.NONE)


def sync_waiting_for_order_object(order_object, changed_fields=None):
    wrapper_order = get_wrapper_order_for_object(order_object)
    if wrapper_order is None:
        return None

    status_change = (changed_fields or {}).get("status")
    current_status = getattr(order_object, "status", None)
    next_status = status_change[1] if status_change else current_status

    if next_status in TERMINAL_ORDER_STATUSES:
        return reset_waiting_for_order(wrapper_order)

    return wrapper_order
