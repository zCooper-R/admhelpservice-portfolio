from datetime import timedelta

import pytest
from unittest import mock
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from django.contrib.contenttypes.models import ContentType

from apps.orders.choices import OrderPrinterCategory, OrderStatus, OrderWaitingFor
from apps.orders.models.base import Order
from apps.orders.models.printer import OrderPrinter
from apps.orders.selectors import OrderDataTableSelector


@pytest.mark.django_db
def test_ajax_create_printer_requires_login():
    client = Client()
    url = reverse('orders:order_printer_create')
    response = client.get(url)
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_order_wrapper_created_with_printer():
    user = get_user_model().objects.create_user(username='u1', password='pass')
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
    assert Order.objects.filter(content_type=ct, object_id=op.pk).exists()


@pytest.mark.django_db
@mock.patch('apps.orders.tasks.task_mail_admins.apply_async')
@mock.patch('django.contrib.messages.views.SuccessMessageMixin.form_valid', return_value=None)
def test_generic_workflow_mail_task_scheduled(
    mock_msg,
    mock_mail,
    settings,
    request_with_user,
):
    settings.DEBUG = False

    from apps.orders.views.mixins import OrderCreateMixin
    from django.views.generic.edit import CreateView

    class V(OrderCreateMixin, CreateView):
        pass

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

    class Form:
        instance = op

        def save(self):
            return op

    view = V()
    view.request = request_with_user

    with mock.patch('apps.orders.views.mixins.transaction.on_commit', lambda fn: fn()):
        with mock.patch('apps.orders.models.base.Order.objects.get') as m_get:
            ct = ContentType.objects.get_for_model(OrderPrinter)
            m_get.return_value = Order(id=1, content_type=ct, object_id=op.pk)
            view.form_valid(Form())

    mock_mail.assert_called_once()


@pytest.mark.django_db
def test_ajax_printer_detail_available_for_owner():
    user = get_user_model().objects.create_user(username='detail_owner', password='pass')
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
    client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert client.login(username='detail_owner', password='pass')

    response = client.get(reverse('orders:order_printer_detail', kwargs={'pk': op.pk}))

    assert response.status_code == 200


@pytest.mark.django_db
def test_ajax_printer_detail_forbidden_for_other_user_without_permission():
    owner = get_user_model().objects.create_user(username='detail_owner_2', password='pass')
    other = get_user_model().objects.create_user(username='detail_other', password='pass')
    op = OrderPrinter.objects.create(
        owner=owner,
        client='Test',
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert client.login(username='detail_other', password='pass')

    response = client.get(reverse('orders:order_printer_detail', kwargs={'pk': op.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_ajax_printer_update_available_for_superuser():
    admin = get_user_model().objects.create_superuser(
        username='detail_admin',
        password='pass',
        email='detail_admin@example.com',
    )
    op = OrderPrinter.objects.create(
        owner=admin,
        client='Test',
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert client.login(username='detail_admin', password='pass')

    response = client.get(reverse('orders:order_printer_update', kwargs={'pk': op.pk}))

    assert response.status_code == 200


@pytest.mark.django_db
def test_ajax_account_create_returns_full_modal_without_category():
    user = get_user_model().objects.create_user(username='account_create_user', password='pass')
    client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert client.login(username='account_create_user', password='pass')

    response = client.get(reverse('orders:order_account_create'))

    assert response.status_code == 200
    assert 'orderFormModal' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_ajax_account_create_returns_full_modal_with_category():
    user = get_user_model().objects.create_user(username='account_partial_user', password='pass')
    client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert client.login(username='account_partial_user', password='pass')

    response = client.get(reverse('orders:order_account_create'), {'category': '0'})

    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'orderFormModal' in content
    assert 'id_category' in content


@pytest.mark.django_db
def test_ajax_vks_create_returns_full_modal():
    user = get_user_model().objects.create_user(
        username='vks_create_user',
        password='pass',
        email='vks@example.com',
    )
    client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert client.login(username='vks_create_user', password='pass')

    response = client.get(reverse('orders:order_vks_create'))

    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'orderFormModal' in content
    assert 'Yandex Telemost' in content


@pytest.mark.django_db
def test_datatable_page_sorts_by_client_for_my_orders():
    user = get_user_model().objects.create_user(username='datatable_client_user', password='pass')

    OrderPrinter.objects.create(
        owner=user,
        client='Яблоко',
        address='Addr 1',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP-1',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    OrderPrinter.objects.create(
        owner=user,
        client='Арбуз',
        address='Addr 2',
        departament='Dep',
        cabinet='2',
        phone='2',
        printer_name='HP-2',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        order_column='client',
        order_dir='asc',
    )

    assert records_total == 2
    assert records_filtered == 2
    assert [row['client'] for row in rows] == ['Арбуз', 'Яблоко']


@pytest.mark.django_db
def test_datatable_page_sorts_by_category_for_my_orders():
    user = get_user_model().objects.create_user(username='datatable_category_user', password='pass')

    OrderPrinter.objects.create(
        owner=user,
        client='Client 1',
        address='Addr 1',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP-1',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    OrderPrinter.objects.create(
        owner=user,
        client='Client 2',
        address='Addr 2',
        departament='Dep',
        cabinet='2',
        phone='2',
        printer_name='HP-2',
        category=OrderPrinterCategory.REFILL,
        status=OrderStatus.ACCEPTED,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        order_column='category',
        order_dir='asc',
    )

    assert records_total == 2
    assert records_filtered == 2
    assert [row['category'] for row in rows] == ['Принтер-Заправка', 'Принтер-Ремонт']


@pytest.mark.django_db
def test_datatable_page_sorts_by_status_for_my_orders():
    user = get_user_model().objects.create_user(username='datatable_status_user', password='pass')

    OrderPrinter.objects.create(
        owner=user,
        client='Client 1',
        address='Addr 1',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP-1',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.DONE,
    )
    OrderPrinter.objects.create(
        owner=user,
        client='Client 2',
        address='Addr 2',
        departament='Dep',
        cabinet='2',
        phone='2',
        printer_name='HP-2',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        order_column='status',
        order_dir='asc',
    )

    assert records_total == 2
    assert records_filtered == 2
    assert [row['status'] for row in rows] == ['В очереди', 'Выполнена']


@pytest.mark.django_db
def test_datatable_page_searches_visible_columns_case_insensitively_by_client():
    user = get_user_model().objects.create_user(username='datatable_search_client_user', password='pass')

    OrderPrinter.objects.create(
        owner=user,
        client='Иван Петров',
        address='Addr 1',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP-1',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    OrderPrinter.objects.create(
        owner=user,
        client='Мария Сидорова',
        address='Addr 2',
        departament='Dep',
        cabinet='2',
        phone='2',
        printer_name='HP-2',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='иван',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 1
    assert [row['client'] for row in rows] == ['Иван Петров']


@pytest.mark.django_db
def test_datatable_page_searches_visible_columns_case_insensitively_by_status():
    user = get_user_model().objects.create_user(username='datatable_search_status_user', password='pass')

    OrderPrinter.objects.create(
        owner=user,
        client='Client 1',
        address='Addr 1',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP-1',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    OrderPrinter.objects.create(
        owner=user,
        client='Client 2',
        address='Addr 2',
        departament='Dep',
        cabinet='2',
        phone='2',
        printer_name='HP-2',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.DONE,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='выполн',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 1
    assert [row['status'] for row in rows] == ['Выполнена']


@pytest.mark.django_db
def test_datatable_page_searches_visible_columns_case_insensitively_by_category():
    user = get_user_model().objects.create_user(username='datatable_search_category_user', password='pass')

    OrderPrinter.objects.create(
        owner=user,
        client='Client 1',
        address='Addr 1',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name='HP-1',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    OrderPrinter.objects.create(
        owner=user,
        client='Client 2',
        address='Addr 2',
        departament='Dep',
        cabinet='2',
        phone='2',
        printer_name='HP-2',
        category=OrderPrinterCategory.REFILL,
        status=OrderStatus.ACCEPTED,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='заправ',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 1
    assert [row['category'] for row in rows] == ['Принтер-Заправка']
def _create_printer_wrapper_order(user, *, client, waiting_for=OrderWaitingFor.NONE, waiting_since=None):
    printer_order = OrderPrinter.objects.create(
        owner=user,
        client=client,
        address='Addr',
        departament='Dep',
        cabinet='1',
        phone='1',
        printer_name=f'HP-{client}',
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    order = Order.objects.get(
        content_type=ContentType.objects.get_for_model(OrderPrinter),
        object_id=printer_order.pk,
    )
    order.waiting_for = waiting_for
    order.waiting_since = waiting_since
    order.save(update_fields=['waiting_for', 'waiting_since'])
    return order


@pytest.mark.django_db
def test_datatable_page_searches_waiting_for_value():
    user = get_user_model().objects.create_user(username='datatable_search_waiting_user', password='pass')
    _create_printer_wrapper_order(
        user,
        client='Executor waiting',
        waiting_for=OrderWaitingFor.EXECUTOR,
        waiting_since=timezone.now(),
    )
    _create_printer_wrapper_order(
        user,
        client='Requester waiting',
        waiting_for=OrderWaitingFor.REQUESTER,
        waiting_since=timezone.now(),
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='executor',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 1
    assert [row['client'] for row in rows] == ['Executor waiting']


@pytest.mark.django_db
def test_datatable_page_filters_by_sla_overdue():
    user = get_user_model().objects.create_user(username='datatable_sla_overdue_user', password='pass')
    now = timezone.now()
    _create_printer_wrapper_order(
        user,
        client='Overdue',
        waiting_for=OrderWaitingFor.EXECUTOR,
        waiting_since=now - timedelta(hours=3),
    )
    _create_printer_wrapper_order(
        user,
        client='Warning',
        waiting_for=OrderWaitingFor.REQUESTER,
        waiting_since=now - timedelta(hours=20),
    )
    _create_printer_wrapper_order(user, client='No SLA')

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        sla_filter='overdue',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 3
    assert records_filtered == 1
    assert [row['client'] for row in rows] == ['Overdue']


@pytest.mark.django_db
def test_datatable_page_filters_by_sla_warning():
    user = get_user_model().objects.create_user(username='datatable_sla_warning_user', password='pass')
    now = timezone.now()
    _create_printer_wrapper_order(
        user,
        client='Overdue',
        waiting_for=OrderWaitingFor.EXECUTOR,
        waiting_since=now - timedelta(hours=3),
    )
    _create_printer_wrapper_order(
        user,
        client='Warning',
        waiting_for=OrderWaitingFor.REQUESTER,
        waiting_since=now - timedelta(hours=20),
    )
    _create_printer_wrapper_order(user, client='No SLA')

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        sla_filter='warning',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 3
    assert records_filtered == 1
    assert [row['client'] for row in rows] == ['Warning']


@pytest.mark.django_db
def test_datatable_page_filters_by_sla_none():
    user = get_user_model().objects.create_user(username='datatable_sla_none_user', password='pass')
    now = timezone.now()
    _create_printer_wrapper_order(
        user,
        client='Overdue',
        waiting_for=OrderWaitingFor.EXECUTOR,
        waiting_since=now - timedelta(hours=3),
    )
    _create_printer_wrapper_order(user, client='No SLA')

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        sla_filter='none',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 1
    assert [row['client'] for row in rows] == ['No SLA']


@pytest.mark.django_db
def test_datatable_page_none_filter_excludes_active_waiting_without_waiting_since():
    user = get_user_model().objects.create_user(username='datatable_sla_none_strict_user', password='pass')
    _create_printer_wrapper_order(user, client='No SLA')
    _create_printer_wrapper_order(
        user,
        client='Broken active waiting',
        waiting_for=OrderWaitingFor.EXECUTOR,
        waiting_since=None,
    )

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        sla_filter='none',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 1
    assert [row['client'] for row in rows] == ['No SLA']


@pytest.mark.django_db
def test_datatable_page_default_sla_filter_does_not_narrow_results():
    user = get_user_model().objects.create_user(username='datatable_sla_all_user', password='pass')
    _create_printer_wrapper_order(user, client='First')
    _create_printer_wrapper_order(user, client='Second')

    records_total, records_filtered, rows = Order.objects.datatable_page(
        user,
        scope='mine',
        start=0,
        length=10,
        search_value='',
        order_column='created_at',
        order_dir='desc',
    )

    assert records_total == 2
    assert records_filtered == 2
    assert len(rows) == 2


def test_datatable_sla_filter_parameter_parsing_is_stable():
    assert OrderDataTableSelector.normalize_sla_filter('warning') == 'warning'
    assert OrderDataTableSelector.normalize_sla_filter('OVERDUE') == 'overdue'
    assert OrderDataTableSelector.normalize_sla_filter('unexpected') == 'all'
    assert OrderDataTableSelector.normalize_sla_filter('') == 'all'
