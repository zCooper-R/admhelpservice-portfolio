from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.orders.choices import OrderPrinterCategory, OrderStatus, OrderWaitingFor
from apps.orders.models.base import Order
from apps.orders.models.printer import OrderPrinter
from apps.orders.services.sla import get_response_deadline, get_sla_state, get_time_left
from apps.orders.utils.datatables import build_waiting_payload


@pytest.mark.django_db
def test_sla_deadline_and_state_for_executor_waiting():
    user = get_user_model().objects.create_user(username="sla_executor", password="pass")
    order = OrderPrinter.objects.create(
        owner=user,
        client="Test",
        address="Addr",
        departament="Dep",
        cabinet="1",
        phone="1",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.IN_WORK,
    )
    wrapper_order = Order.objects.get(object_id=order.pk)
    wrapper_order.waiting_for = OrderWaitingFor.EXECUTOR
    wrapper_order.waiting_since = timezone.now() - timedelta(minutes=90)

    deadline = get_response_deadline(wrapper_order)

    assert deadline == wrapper_order.waiting_since + timedelta(hours=2)
    assert get_sla_state(wrapper_order) == "ok"
    assert timedelta(minutes=29) <= get_time_left(wrapper_order) <= timedelta(minutes=31)


@pytest.mark.django_db
def test_sla_warning_and_overdue_payload():
    user = get_user_model().objects.create_user(username="sla_requester", password="pass")
    order = OrderPrinter.objects.create(
        owner=user,
        client="Test",
        address="Addr",
        departament="Dep",
        cabinet="1",
        phone="1",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.IN_WORK,
    )
    wrapper_order = Order.objects.get(object_id=order.pk)

    wrapper_order.waiting_for = OrderWaitingFor.REQUESTER
    wrapper_order.waiting_since = timezone.now() - timedelta(hours=20)
    assert get_sla_state(wrapper_order) == "warning"
    assert "Осталось:" in build_waiting_payload(wrapper_order)["detail"]

    wrapper_order.waiting_since = timezone.now() - timedelta(hours=25)
    assert get_sla_state(wrapper_order) == "overdue"
    assert "Просрочено на" in build_waiting_payload(wrapper_order)["detail"]
