from apps.order_communication.constants import MessageVisibility
from apps.orders.services.workflow import (
    user_can_execute_order,
    user_can_moderate_order,
    user_can_update_order,
    user_can_view_order,
)


def _get_order_object(order):
    return getattr(order, "content_object", None)


def is_requester(user, order) -> bool:
    return bool(getattr(user, "is_authenticated", False) and user == getattr(order, "owner", None))


def is_staff_actor(user, order) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True

    order_object = _get_order_object(order)
    if order_object is None:
        return False
    return user_can_execute_order(user, order_object) or user_can_moderate_order(user, order_object)


def can_view_thread(user, order) -> bool:
    order_object = _get_order_object(order)
    if order_object is None:
        return False
    return user_can_view_order(user, order_object)


def can_view_message(user, message) -> bool:
    order = message.thread.order
    if not can_view_thread(user, order):
        return False
    if message.visibility == MessageVisibility.STAFF_ONLY:
        return is_staff_actor(user, order)
    return True


def can_post_public_reply(user, order) -> bool:
    return can_view_thread(user, order) and (is_requester(user, order) or is_staff_actor(user, order))


def can_post_internal_note(user, order) -> bool:
    return can_view_thread(user, order) and is_staff_actor(user, order)


def can_edit_message(user, message) -> bool:
    order = message.thread.order
    if not can_view_message(user, message):
        return False
    if user.is_superuser:
        return True
    if is_staff_actor(user, order) and user_can_update_order(user, _get_order_object(order)):
        return message.author_id == user.pk or message.visibility == MessageVisibility.STAFF_ONLY
    return message.author_id == user.pk and message.visibility == MessageVisibility.REQUESTER_AND_STAFF


def can_delete_message(user, message) -> bool:
    order = message.thread.order
    if not can_view_message(user, message):
        return False
    if user.is_superuser:
        return True
    return is_staff_actor(user, order) and user_can_update_order(user, _get_order_object(order))


def can_download_attachment(user, attachment) -> bool:
    if getattr(attachment, "is_deleted", False):
        return False
    return can_view_message(user, attachment.message)
