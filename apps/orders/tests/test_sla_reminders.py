from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from urllib.parse import urlencode
from django.utils import timezone

from apps.notifications.constants import NotificationEventType
from apps.notifications.models import Notification
from apps.orders.choices import OrderPrinterCategory, OrderStatus, OrderWaitingFor
from apps.orders.models.base import Order
from apps.orders.models.printer import OrderPrinter
from apps.orders.services.sla_reminders import (
    build_sla_reminder_cache_key,
    get_sla_reminder_recipient,
    process_order_sla_reminder,
    should_send_sla_reminder,
)
from apps.orders.tasks.sla import task_process_sla_reminders
from apps.users.models import SupportSpecialist, TechnicalGroup


@pytest.fixture
def sla_reminder_setup(db):
    user_model = get_user_model()
    requester = user_model.objects.create_user(username="sla_requester_user", password="pass")
    executor_user = user_model.objects.create_user(username="sla_executor_user", password="pass")
    technical_group = TechnicalGroup.objects.create(name="SLA", priority=TechnicalGroup.Priority.HIGH)
    specialist = SupportSpecialist.objects.create(user=executor_user, technical_group=technical_group, is_available=True)

    order_object = OrderPrinter.objects.create(
        owner=requester,
        support_specialist=specialist,
        client="Test",
        address="Addr",
        departament="Dep",
        cabinet="1",
        phone="1",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.IN_WORK,
    )
    order = Order.objects.get(object_id=order_object.pk)
    return {
        "requester": requester,
        "executor_user": executor_user,
        "specialist": specialist,
        "order_object": order_object,
        "order": order,
    }


@pytest.fixture(autouse=True)
def clear_sla_cache():
    cache.clear()
    yield
    cache.clear()


def _set_waiting(order, *, waiting_for, waiting_since):
    order.waiting_for = waiting_for
    order.waiting_since = waiting_since
    order.save(update_fields=["waiting_for", "waiting_since", "updated_at"])


@pytest.mark.django_db
def test_warning_reminder_sent_once_and_suppressed_by_cache(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    recipient = sla_reminder_setup["requester"]
    _set_waiting(order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=20))

    first = process_order_sla_reminder(order)
    second = process_order_sla_reminder(order)

    assert first is not None
    assert second is None
    notifications = Notification.objects.filter(recipient=recipient, event_type=NotificationEventType.ORDER_SLA_REMINDER)
    assert notifications.count() == 1
    assert notifications.first().metadata["sla_state"] == "warning"


@pytest.mark.django_db
def test_overdue_reminder_sent_once_and_suppressed_by_cache(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    recipient = sla_reminder_setup["requester"]
    _set_waiting(order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=25))

    first = process_order_sla_reminder(order)
    second = process_order_sla_reminder(order)

    assert first is not None
    assert second is None
    notifications = Notification.objects.filter(recipient=recipient, event_type=NotificationEventType.ORDER_SLA_REMINDER)
    assert notifications.count() == 1
    assert notifications.first().metadata["sla_state"] == "overdue"


@pytest.mark.django_db
def test_reminder_is_not_sent_for_ok(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    _set_waiting(order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=1))

    assert process_order_sla_reminder(order) is None
    assert Notification.objects.count() == 0


@pytest.mark.django_db
def test_reminder_is_not_sent_for_none(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    _set_waiting(order, waiting_for=OrderWaitingFor.NONE, waiting_since=None)

    assert process_order_sla_reminder(order) is None
    assert Notification.objects.count() == 0


@pytest.mark.django_db
def test_executor_waiting_sends_only_to_assigned_executor(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    executor_user = sla_reminder_setup["executor_user"]
    requester = sla_reminder_setup["requester"]
    _set_waiting(order, waiting_for=OrderWaitingFor.EXECUTOR, waiting_since=timezone.now() - timedelta(hours=3))

    process_order_sla_reminder(order)

    notifications = Notification.objects.filter(event_type=NotificationEventType.ORDER_SLA_REMINDER)
    assert notifications.count() == 1
    assert notifications.first().recipient == executor_user
    assert notifications.first().recipient != requester


@pytest.mark.django_db
def test_executor_waiting_without_assigned_executor_sends_to_nobody(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    order_object = sla_reminder_setup["order_object"]
    order_object.support_specialist = None
    order_object.save(update_fields=["support_specialist", "updated_at"])
    order.refresh_from_db()
    order.content_object = order_object
    _set_waiting(order, waiting_for=OrderWaitingFor.EXECUTOR, waiting_since=timezone.now() - timedelta(hours=3))

    assert get_sla_reminder_recipient(order) is None
    assert process_order_sla_reminder(order) is None
    assert Notification.objects.count() == 0


@pytest.mark.django_db
def test_requester_waiting_sends_only_to_requester(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    requester = sla_reminder_setup["requester"]
    executor_user = sla_reminder_setup["executor_user"]
    _set_waiting(order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=25))

    process_order_sla_reminder(order)

    notifications = Notification.objects.filter(event_type=NotificationEventType.ORDER_SLA_REMINDER)
    assert notifications.count() == 1
    assert notifications.first().recipient == requester
    assert notifications.first().recipient != executor_user
    assert notifications.first().target_url == f"{reverse('orders:orders_list')}?{urlencode({'modal': order.get_absolute_url()})}"


@pytest.mark.django_db
def test_cache_key_format_is_stable(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    recipient = sla_reminder_setup["requester"]

    assert build_sla_reminder_cache_key(order, recipient, "warning") == f"sla_reminder:{order.id}:{recipient.id}:warning"


@pytest.mark.django_db
def test_atomic_dedupe_uses_cache_add(sla_reminder_setup):
    order = sla_reminder_setup["order"]
    recipient = sla_reminder_setup["requester"]

    with patch("apps.orders.services.sla_reminders.cache.add", side_effect=[True, False]) as mock_add:
        assert should_send_sla_reminder(order, recipient, "warning") is True
        assert should_send_sla_reminder(order, recipient, "warning") is False

    assert mock_add.call_count == 2


@pytest.mark.django_db
def test_periodic_task_processes_only_relevant_orders(sla_reminder_setup):
    relevant_order = sla_reminder_setup["order"]
    _set_waiting(relevant_order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=25))

    other_object = OrderPrinter.objects.create(
        owner=sla_reminder_setup["requester"],
        client="Other",
        address="Addr",
        departament="Dep",
        cabinet="2",
        phone="2",
        printer_name="HP-2",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.IN_WORK,
    )
    other_order = Order.objects.get(object_id=other_object.pk)
    _set_waiting(other_order, waiting_for=OrderWaitingFor.NONE, waiting_since=None)

    with patch("apps.orders.tasks.sla.process_order_sla_reminder", wraps=process_order_sla_reminder) as mock_process:
        sent_count = task_process_sla_reminders()

    assert sent_count == 1
    processed_ids = [call.args[0].id for call in mock_process.call_args_list]
    assert processed_ids == [relevant_order.id]


@pytest.mark.django_db
def test_periodic_task_continues_when_one_order_fails(sla_reminder_setup):
    first_order = sla_reminder_setup["order"]
    _set_waiting(first_order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=25))

    other_object = OrderPrinter.objects.create(
        owner=sla_reminder_setup["requester"],
        client="Other",
        address="Addr",
        departament="Dep",
        cabinet="2",
        phone="2",
        printer_name="HP-2",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.IN_WORK,
    )
    second_order = Order.objects.get(object_id=other_object.pk)
    _set_waiting(second_order, waiting_for=OrderWaitingFor.REQUESTER, waiting_since=timezone.now() - timedelta(hours=25))

    original = process_order_sla_reminder

    processed_ids = []

    def side_effect(order):
        processed_ids.append(order.id)
        if order.id == first_order.id:
            raise RuntimeError("boom")
        return original(order)

    with patch("apps.orders.tasks.sla.process_order_sla_reminder", side_effect=side_effect):
        sent_count = task_process_sla_reminders()

    assert sent_count == 1
    assert Notification.objects.filter(event_type=NotificationEventType.ORDER_SLA_REMINDER).count() == 1
    assert len(processed_ids) == 2
    assert set(processed_ids) == {first_order.id, second_order.id}
