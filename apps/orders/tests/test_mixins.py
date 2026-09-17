# test_mixins.py
import pytest
from unittest import mock
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.views.generic.edit import CreateView

from apps.order_communication.models import OrderMessage
from apps.orders.models.base import Order
from apps.orders.models.printer import OrderPrinter
from apps.orders.choices import OrderPrinterCategory, OrderStatus, OrderWaitingFor
from apps.orders.views.mixins import OrderCreateMixin, OrderUpdateMixin
from apps.users.models import SupportSpecialist, TechnicalGroup


class DummyView(OrderCreateMixin, CreateView):
    request = None
    object = None
    telegram_tasks = []

    def is_ajax(self, request):
        return False


class DummyUpdateView(OrderUpdateMixin):
    request = None
    object = None


@pytest.mark.django_db
@mock.patch('django.contrib.messages.views.SuccessMessageMixin.form_valid', return_value=None)
@mock.patch("apps.orders.models.base.Order.objects.get")
@mock.patch("apps.orders.tasks.task_mail_admins.apply_async")
def test_order_create_mixin_runs_tasks(
    mock_mail_admins,
    mock_order_get,
    mock_msg_form_valid,
    request_with_user,
):
    user = request_with_user.user
    op = OrderPrinter.objects.create(
        owner=user,
        client='Test',
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    ct = ContentType.objects.get_for_model(OrderPrinter)
    mock_order = Order(id=99, content_type=ct, object_id=op.pk)
    mock_order_get.return_value = mock_order

    class Form:
        instance = op

        def save(self):
            return op

    view = DummyView()
    view.request = request_with_user

    with mock.patch('apps.orders.views.mixins.transaction.on_commit', lambda fn: fn()):
        with mock.patch('apps.notifications.services.transaction.on_commit', lambda fn: fn()):
            view.form_valid(Form())

    mock_mail_admins.assert_called_once()


def test_all_orders_have_wrapper_mixin():
    from django.apps import apps
    from apps.orders.models.mixins import OrderWrapperMixin
    from apps.orders.models.base import BaseOrder

    for model in apps.get_models():
        if not issubclass(model, BaseOrder) or model is BaseOrder:
            continue
        if model._meta.model_name == 'dummyordermodel':
            continue
        assert issubclass(model, OrderWrapperMixin), f"{model.__name__} missing OrderWrapperMixin"


@pytest.mark.django_db
@mock.patch('django.contrib.messages.views.SuccessMessageMixin.form_valid', return_value=None)
@mock.patch("apps.orders.views.mixins.emit_order_created_notification")
def test_order_create_mixin_creates_ticket_system_event(
    mock_emit_order_created_notification,
    mock_msg_form_valid,
    request_with_user,
):
    user = request_with_user.user
    op = OrderPrinter(
        owner=user,
        client='Test',
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )

    class Form:
        instance = op

        def save(self):
            self.instance.save()
            return self.instance

    view = DummyView()
    view.request = request_with_user

    with mock.patch('apps.orders.views.mixins.transaction.on_commit', lambda fn: fn()):
        view.form_valid(Form())

    system_events = list(OrderMessage.objects.filter(message_type="system_event").values_list("body", flat=True))
    assert system_events == ["Заявка создана"]
    mock_emit_order_created_notification.assert_called_once()


@pytest.mark.django_db
@mock.patch("apps.orders.views.mixins.emit_order_updated_notifications")
def test_order_update_mixin_creates_status_and_assignment_system_events(mock_emit_order_updated_notifications):
    user_model = get_user_model()
    actor = user_model.objects.create_user(username="update_actor", password="pass", full_name="Update Actor")
    specialist_user = user_model.objects.create_user(
        username="assigned_specialist",
        password="pass",
        full_name="Assigned Specialist",
    )
    replacement_user = user_model.objects.create_user(
        username="replacement_specialist",
        password="pass",
        full_name="Replacement Specialist",
    )

    technical_group = TechnicalGroup.objects.create(name="Mixins", priority=TechnicalGroup.Priority.HIGH)
    specialist = SupportSpecialist.objects.create(user=specialist_user, technical_group=technical_group, is_available=True)
    replacement = SupportSpecialist.objects.create(
        user=replacement_user,
        technical_group=technical_group,
        is_available=True,
    )

    order = OrderPrinter.objects.create(
        owner=actor,
        support_specialist=specialist,
        client='Test',
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    order.status = OrderStatus.IN_WORK
    order.support_specialist = replacement

    class Form:
        instance = order

        def save(self):
            self.instance.save()
            return self.instance

    request = RequestFactory().post("/")
    request.user = actor
    view = DummyUpdateView()
    view.request = request

    response = view.form_valid(Form())

    assert response.status_code == 200
    system_events = list(OrderMessage.objects.filter(message_type="system_event").values_list("body", flat=True))
    assert system_events == [
        "Статус изменён: В очереди -> В работе",
        "Исполнитель изменён: Assigned Specialist -> Replacement Specialist",
    ]
    mock_emit_order_updated_notifications.assert_called_once()


@pytest.mark.django_db
@mock.patch("apps.orders.views.mixins.emit_order_updated_notifications")
def test_order_update_mixin_resets_waiting_for_terminal_status(mock_emit_order_updated_notifications):
    user_model = get_user_model()
    actor = user_model.objects.create_user(username="waiting_actor", password="pass", full_name="Waiting Actor")

    order = OrderPrinter.objects.create(
        owner=actor,
        client='Test',
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.IN_WORK,
    )
    wrapper_order = Order.objects.get(object_id=order.pk)
    wrapper_order.waiting_for = OrderWaitingFor.REQUESTER
    wrapper_order.waiting_since = wrapper_order.created_at
    wrapper_order.save(update_fields=["waiting_for", "waiting_since", "updated_at"])

    order.status = OrderStatus.DONE

    class Form:
        instance = order

        def save(self):
            self.instance.save()
            return self.instance

    request = RequestFactory().post("/")
    request.user = actor
    view = DummyUpdateView()
    view.request = request

    response = view.form_valid(Form())

    assert response.status_code == 200
    wrapper_order.refresh_from_db()
    assert wrapper_order.waiting_for == OrderWaitingFor.NONE
    assert wrapper_order.waiting_since is None
    mock_emit_order_updated_notifications.assert_called_once()
