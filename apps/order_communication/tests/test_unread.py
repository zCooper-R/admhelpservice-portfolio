import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.order_communication.constants import MessageType, MessageVisibility
from apps.order_communication.models import OrderMessage, OrderThread
from apps.order_communication.services.messages import create_public_message
from apps.order_communication.services.read_state import get_first_unread_message_id, get_thread_unread_count, mark_thread_read
from apps.order_communication.selectors.unread import get_unread_count_by_order_ids
from apps.orders.choices import OrderPrinterCategory, OrderStatus, OrderWaitingFor
from apps.orders.models.base import Order
from apps.orders.models.printer import OrderPrinter


@pytest.fixture
def discussion_setup(db):
    user_model = get_user_model()
    requester = user_model.objects.create_user(username="discussion_requester", password="pass")
    staff_author = user_model.objects.create_superuser(
        username="discussion_staff_author",
        password="pass",
        email="discussion_staff_author@example.com",
    )
    staff_reader = user_model.objects.create_superuser(
        username="discussion_staff_reader",
        password="pass",
        email="discussion_staff_reader@example.com",
    )

    order_object = OrderPrinter.objects.create(
        owner=requester,
        client="Иван Иванов",
        address="Адрес",
        departament="Отдел",
        cabinet="101",
        phone="123",
        printer_name="HP LaserJet",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
    )
    order = Order.objects.get(object_id=order_object.pk)
    thread = OrderThread.objects.create(order=order, created_by=staff_author)

    return {
        "requester": requester,
        "staff_author": staff_author,
        "staff_reader": staff_reader,
        "order": order,
        "thread": thread,
    }


@pytest.mark.django_db
def test_requester_unread_count_ignores_internal_notes_and_own_messages(discussion_setup):
    thread = discussion_setup["thread"]
    requester = discussion_setup["requester"]
    staff_author = discussion_setup["staff_author"]

    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Публичный ответ",
    )
    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.INTERNAL_NOTE,
        visibility=MessageVisibility.STAFF_ONLY,
        body="Внутренняя заметка",
    )
    OrderMessage.objects.create(
        thread=thread,
        author=requester,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Мой ответ",
    )

    assert get_thread_unread_count(thread, requester) == 1


@pytest.mark.django_db
def test_mark_thread_read_uses_latest_visible_message_for_requester(discussion_setup):
    thread = discussion_setup["thread"]
    requester = discussion_setup["requester"]
    staff_author = discussion_setup["staff_author"]

    public_message = OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Видимое сообщение",
    )
    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.INTERNAL_NOTE,
        visibility=MessageVisibility.STAFF_ONLY,
        body="Скрытая заметка",
    )

    read_state = mark_thread_read(thread, requester)

    assert read_state.last_read_message_id == public_message.id
    assert get_thread_unread_count(thread, requester) == 0


@pytest.mark.django_db
def test_first_unread_message_id_uses_first_visible_unread_message(discussion_setup):
    thread = discussion_setup["thread"]
    requester = discussion_setup["requester"]
    staff_author = discussion_setup["staff_author"]

    first_public = OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Первое видимое непрочитанное",
    )
    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.INTERNAL_NOTE,
        visibility=MessageVisibility.STAFF_ONLY,
        body="Скрытая заметка",
    )
    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Второе видимое непрочитанное",
    )

    assert get_first_unread_message_id(thread, requester) == first_public.id


@pytest.mark.django_db
def test_bulk_unread_counts_and_datatable_page_include_discussion_counts(discussion_setup):
    order = discussion_setup["order"]
    thread = discussion_setup["thread"]
    requester = discussion_setup["requester"]
    staff_author = discussion_setup["staff_author"]

    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Новый ответ",
    )

    unread_by_order = get_unread_count_by_order_ids([order.id], requester)
    assert unread_by_order[order.id] == 1

    records_total, records_filtered, rows = Order.objects.datatable_page(
        requester,
        scope="mine",
        start=0,
        length=10,
        search_value="",
        order_column="created_at",
        order_dir="desc",
    )

    assert records_total == 1
    assert records_filtered == 1
    assert rows[0]["discussion_unread_count"] == 1


@pytest.mark.django_db
def test_global_ui_summary_returns_notifications_and_discussion_counts(discussion_setup):
    order = discussion_setup["order"]
    thread = discussion_setup["thread"]
    requester = discussion_setup["requester"]
    staff_author = discussion_setup["staff_author"]

    OrderMessage.objects.create(
        thread=thread,
        author=staff_author,
        message_type=MessageType.PUBLIC_REPLY,
        visibility=MessageVisibility.REQUESTER_AND_STAFF,
        body="Непрочитанное сообщение",
    )

    client = Client(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert client.login(username=requester.username, password="pass")

    response = client.get(reverse("orders:ui_summary"), {"order_ids": [order.id]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["notifications"]["unread_count"] == 0
    assert payload["discussion"]["counts"][str(order.id)] == 1
    assert payload["orders"]["statuses"][str(order.id)] == order.content_object.get_status_display()


@pytest.mark.django_db
def test_public_reply_updates_waiting_for_side(discussion_setup):
    order = discussion_setup["order"]
    requester = discussion_setup["requester"]
    staff_author = discussion_setup["staff_author"]

    create_public_message(order, requester, "Нужна помощь")
    order.refresh_from_db()
    assert order.waiting_for == OrderWaitingFor.EXECUTOR
    assert order.waiting_since is not None

    create_public_message(order, staff_author, "Берём в работу")
    order.refresh_from_db()
    assert order.waiting_for == OrderWaitingFor.REQUESTER
    assert order.waiting_since is not None


@pytest.mark.django_db
def test_terminal_status_keeps_waiting_for_none_after_public_reply(discussion_setup):
    order = discussion_setup["order"]
    requester = discussion_setup["requester"]
    order_object = order.content_object
    order_object.status = OrderStatus.CLOSED
    order_object.save(update_fields=["status", "updated_at"])

    create_public_message(order, requester, "Есть уточнение")

    order.refresh_from_db()
    assert order.waiting_for == OrderWaitingFor.NONE
    assert order.waiting_since is None


@pytest.mark.django_db
def test_global_ui_summary_returns_waiting_labels(discussion_setup):
    order = discussion_setup["order"]
    requester = discussion_setup["requester"]

    create_public_message(order, requester, "Жду ответ")
    order.refresh_from_db()

    client = Client(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert client.login(username=requester.username, password="pass")

    response = client.get(reverse("orders:ui_summary"), {"order_ids": [order.id]})

    assert response.status_code == 200
    payload = response.json()
    waiting_payload = payload["orders"]["waiting"][str(order.id)]
    assert waiting_payload["label"] == order.get_waiting_for_display()
    assert waiting_payload["variant"] == OrderWaitingFor.EXECUTOR


@pytest.mark.django_db
def test_public_reply_api_returns_immediate_order_summary(discussion_setup):
    order = discussion_setup["order"]
    requester = discussion_setup["requester"]

    client = Client(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert client.login(username=requester.username, password="pass")

    response = client.post(
        reverse("order_communication:public_reply_create", kwargs={"order_id": order.id}),
        {"body": "Нужна помощь"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["order_summary"]["id"] == order.id
    assert payload["order_summary"]["status"] == order.content_object.get_status_display()
    assert payload["order_summary"]["waiting_for"] == OrderWaitingFor.EXECUTOR.label
    assert payload["thread_summary"]["messages_count"] == 1
    assert payload["thread_summary"]["latest_visible_message_at"]
