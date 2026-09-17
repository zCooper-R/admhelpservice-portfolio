from django.contrib.contenttypes.models import ContentType

from apps.order_communication.constants import MessageVisibility
from apps.order_communication.services.messages import create_system_event
from apps.orders.models.base import Order


def _get_wrapper_order(order_object):
    return (
        Order.objects.select_related("owner", "content_type")
        .filter(
            content_type=ContentType.objects.get_for_model(order_object, for_concrete_model=False),
            object_id=order_object.pk,
        )
        .first()
    )


def _get_status_display(order_object, value):
    if value in (None, ""):
        return "Без статуса"

    status_field = order_object._meta.get_field("status")
    return dict(status_field.flatchoices).get(value, str(value))


def _get_specialist_name(specialist):
    if specialist is None:
        return "Не назначен"
    return str(specialist)


def emit_ticket_created_event(order, actor):
    return create_system_event(
        order,
        actor=actor,
        event_type="ticket_created",
        payload={"source": "order_lifecycle", "label": "Заявка создана"},
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Заявка создана",
    )


def emit_order_status_changed_event(order, actor, old_status, new_status):
    old_status_display = _get_status_display(order.content_object, old_status)
    new_status_display = _get_status_display(order.content_object, new_status)
    return create_system_event(
        order,
        actor=actor,
        event_type="status_changed",
        payload={
            "old_status": old_status,
            "new_status": new_status,
            "old_status_display": old_status_display,
            "new_status_display": new_status_display,
        },
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body=f"Статус изменён: {old_status_display} -> {new_status_display}",
    )


def emit_assignment_changed_event(order, actor, old_specialist, new_specialist):
    old_specialist_name = _get_specialist_name(old_specialist)
    new_specialist_name = _get_specialist_name(new_specialist)

    if old_specialist and new_specialist:
        body = f"Исполнитель изменён: {old_specialist_name} -> {new_specialist_name}"
    elif new_specialist:
        body = f"Назначен исполнитель: {new_specialist_name}"
    else:
        body = f"Исполнитель снят: {old_specialist_name}"

    return create_system_event(
        order,
        actor=actor,
        event_type="assignment_changed",
        payload={
            "old_specialist_id": getattr(old_specialist, "pk", None),
            "new_specialist_id": getattr(new_specialist, "pk", None),
            "old_specialist_name": old_specialist_name,
            "new_specialist_name": new_specialist_name,
        },
        visibility=MessageVisibility.STAFF_ONLY,
        body=body,
    )


def emit_order_created_timeline_event(order_object, actor):
    wrapper_order = _get_wrapper_order(order_object)
    if wrapper_order is None:
        return []
    return [emit_ticket_created_event(wrapper_order, actor)]


def emit_order_lifecycle_events(order_object, actor, changed_fields):
    wrapper_order = _get_wrapper_order(order_object)
    if wrapper_order is None or not changed_fields:
        return []

    events = []

    status_change = changed_fields.get("status")
    if status_change and status_change[0] != status_change[1]:
        events.append(
            emit_order_status_changed_event(
                wrapper_order,
                actor=actor,
                old_status=status_change[0],
                new_status=status_change[1],
            )
        )

    specialist_change = changed_fields.get("support_specialist")
    if specialist_change and specialist_change[0] != specialist_change[1]:
        events.append(
            emit_assignment_changed_event(
                wrapper_order,
                actor=actor,
                old_specialist=specialist_change[0],
                new_specialist=specialist_change[1],
            )
        )

    return events
