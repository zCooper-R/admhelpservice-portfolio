import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from apps.order_communication.constants import MessageType, MessageVisibility
from apps.order_communication.selectors.messages import get_visible_messages_for_thread
from apps.order_communication.services.timeline import (
    emit_assignment_changed_event,
    emit_order_status_changed_event,
    emit_ticket_created_event,
)
from apps.orders.choices import OrderPrinterCategory, OrderStatus
from apps.orders.models.base import Order
from apps.orders.models.printer import OrderPrinter
from apps.orders.models.workflow import OrderWorkflowRule
from apps.users.models import SupportSpecialist, TechnicalGroup


def _create_user(username, *, is_superuser=False):
    user_model = get_user_model()
    if is_superuser:
        return user_model.objects.create_superuser(
            username=username,
            password="pass",
            email=f"{username}@example.com",
            full_name=username.replace("_", " ").title(),
        )
    return user_model.objects.create_user(
        username=username,
        password="pass",
        full_name=username.replace("_", " ").title(),
    )


def _grant_perms(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))


@pytest.fixture
def system_event_setup(db):
    requester = _create_user("system_event_requester")
    moderator = _create_user("system_event_moderator")
    staff_user = _create_user("system_event_staff")
    replacement_user = _create_user("system_event_replacement")

    moderator_group = Group.objects.create(name="system_event_moderators")
    moderator.groups.add(moderator_group)
    _grant_perms(moderator, "view_orderprinter", "change_orderprinter")

    technical_group = TechnicalGroup.objects.create(name="System events", priority=TechnicalGroup.Priority.HIGH)
    specialist = SupportSpecialist.objects.create(user=staff_user, technical_group=technical_group, is_available=True)
    replacement = SupportSpecialist.objects.create(
        user=replacement_user,
        technical_group=technical_group,
        is_available=True,
    )

    order_object = OrderPrinter.objects.create(
        owner=requester,
        support_specialist=specialist,
        client="Иван Иванов",
        address="Адрес",
        departament="Отдел",
        cabinet="101",
        phone="123",
        printer_name="HP LaserJet",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    OrderWorkflowRule.objects.create(
        content_type=ContentType.objects.get_for_model(OrderPrinter, for_concrete_model=False),
        technical_group=technical_group,
        auto_assign_enabled=False,
    ).moderator_groups.add(moderator_group)
    order = Order.objects.get(object_id=order_object.pk)

    return {
        "requester": requester,
        "moderator": moderator,
        "specialist": specialist,
        "replacement": replacement,
        "order": order,
    }


@pytest.mark.django_db
def test_system_events_render_readable_russian_bodies(system_event_setup):
    order = system_event_setup["order"]
    moderator = system_event_setup["moderator"]

    created_event = emit_ticket_created_event(order, moderator)
    status_event = emit_order_status_changed_event(order, moderator, OrderStatus.ACCEPTED, OrderStatus.IN_WORK)
    assignment_event = emit_assignment_changed_event(
        order,
        moderator,
        system_event_setup["specialist"],
        system_event_setup["replacement"],
    )

    assert created_event.message_type == MessageType.SYSTEM_EVENT
    assert created_event.body == "Заявка создана"
    assert created_event.visibility == MessageVisibility.REQUESTER_AND_STAFF

    assert status_event.body == "Статус изменён: В очереди -> В работе"
    assert status_event.payload["old_status_display"] == "В очереди"
    assert status_event.payload["new_status_display"] == "В работе"
    assert status_event.visibility == MessageVisibility.REQUESTER_AND_STAFF

    assert assignment_event.body == "Исполнитель изменён: System Event Staff -> System Event Replacement"
    assert assignment_event.payload["old_specialist_name"] == "System Event Staff"
    assert assignment_event.payload["new_specialist_name"] == "System Event Replacement"
    assert assignment_event.visibility == MessageVisibility.STAFF_ONLY


@pytest.mark.django_db
def test_requester_does_not_see_staff_only_assignment_system_event(system_event_setup):
    order = system_event_setup["order"]
    moderator = system_event_setup["moderator"]

    emit_ticket_created_event(order, moderator)
    emit_assignment_changed_event(
        order,
        moderator,
        system_event_setup["specialist"],
        system_event_setup["replacement"],
    )

    requester_messages = list(get_visible_messages_for_thread(order.communication_thread, system_event_setup["requester"]))
    moderator_messages = list(get_visible_messages_for_thread(order.communication_thread, moderator))

    assert [message.body for message in requester_messages] == ["Заявка создана"]
    assert [message.body for message in moderator_messages] == [
        "Заявка создана",
        "Исполнитель изменён: System Event Staff -> System Event Replacement",
    ]
