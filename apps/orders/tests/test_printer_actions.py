from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from apps.orders.choices import OrderPrinterCategory, OrderStatus
from apps.orders.models import OrderPrinter
from apps.users.models import SupportSpecialist


def create_user(username: str):
    return get_user_model().objects.create_user(username=username, password="pass", full_name=username)


def create_specialist(username: str):
    user = create_user(username)
    specialist = SupportSpecialist.objects.create(user=user, is_available=True)
    return user, specialist


def create_order(owner, *, specialist=None):
    return OrderPrinter.objects.create(
        owner=owner,
        support_specialist=specialist,
        client="Test",
        address="Address",
        departament="Dept",
        cabinet="101",
        phone="123",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
        description="Description",
    )


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_executor_can_send_printer_order_to_techno_service(monkeypatch):
    owner = create_user("owner_printer_action")
    executor_user, specialist = create_specialist("executor_printer_action")
    order = create_order(owner, specialist=specialist)
    delay_mock = Mock()
    monkeypatch.setattr("apps.orders.views.printer.task_mail_organisation_from_admin_panel.delay", delay_mock)

    client = Client(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert client.login(username="executor_printer_action", password="pass")

    response = client.post(reverse("orders:order_printer_send_to_techno_service", kwargs={"pk": order.pk}))

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.emailed_to_organisation is True
    assert order.status == OrderStatus.IN_WORK
    delay_mock.assert_called_once_with(order.id)
    assert response.json()["success"] is True


@pytest.mark.django_db
def test_executor_can_open_send_to_techno_service_confirmation():
    owner = create_user("owner_printer_confirm")
    _, specialist = create_specialist("executor_printer_confirm")
    order = create_order(owner, specialist=specialist)

    client = Client(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert client.login(username="executor_printer_confirm", password="pass")

    response = client.get(reverse("orders:order_printer_send_to_techno_service_confirm", kwargs={"pk": order.pk}))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Техно-Сервис" in content
    assert "Подтвердите действие" in content or "Отправка во внешнюю организацию" in content
