import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch

from apps.notifications.constants import NotificationEventType
from apps.notifications.models import Notification
from apps.order_communication.services.messages import create_internal_note, create_public_message
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
def notification_setup(db):
    requester = _create_user("discussion_requester")
    specialist_user = _create_user("assigned_specialist")
    moderator = _create_user("workflow_moderator")
    superuser = _create_user("discussion_admin", is_superuser=True)

    moderator_group = Group.objects.create(name="discussion_moderators")
    moderator.groups.add(moderator_group)
    _grant_perms(moderator, "view_orderprinter", "change_orderprinter")

    technical_group = TechnicalGroup.objects.create(name="Print", priority=TechnicalGroup.Priority.HIGH)
    specialist = SupportSpecialist.objects.create(user=specialist_user, technical_group=technical_group, is_available=True)

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
        "specialist_user": specialist_user,
        "specialist": specialist,
        "moderator": moderator,
        "superuser": superuser,
        "order": order,
    }


def _run_on_commit_immediately():
    return patch("apps.order_communication.services.notifications.transaction.on_commit", side_effect=lambda fn: fn())


@pytest.mark.django_db
def test_public_reply_from_requester_notifies_staff_only(notification_setup):
    with _run_on_commit_immediately():
        message = create_public_message(
            notification_setup["order"],
            notification_setup["requester"],
            "Проверьте, пожалуйста, принтер в кабинете 101.",
        )

    notifications = Notification.objects.order_by("recipient_id")
    recipients = {notification.recipient for notification in notifications}

    assert recipients == {
        notification_setup["specialist_user"],
        notification_setup["moderator"],
        notification_setup["superuser"],
    }
    assert notification_setup["requester"] not in recipients
    assert all(item.event_type == NotificationEventType.ORDER_COMMENT_ADDED for item in notifications)
    assert all(item.metadata["message_id"] == message.pk for item in notifications)
    assert all(item.metadata["visibility"] == message.visibility for item in notifications)
    assert all("modal_tab=discussion" in item.target_url for item in notifications)


@pytest.mark.django_db
def test_public_reply_from_staff_notifies_requester_only(notification_setup):
    with _run_on_commit_immediately():
        create_public_message(
            notification_setup["order"],
            notification_setup["specialist_user"],
            "Готово, можно проверять.",
        )

    notifications = list(Notification.objects.all())
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.recipient == notification_setup["requester"]
    assert notification.actor == notification_setup["specialist_user"]
    assert notification.title == f"Новый ответ по заявке №{notification_setup['order'].pk}"
    assert "Assigned Specialist: Готово, можно проверять." == notification.body


@pytest.mark.django_db
def test_internal_note_notifies_staff_but_not_requester(notification_setup):
    with _run_on_commit_immediately():
        message = create_internal_note(
            notification_setup["order"],
            notification_setup["moderator"],
            "Нужно согласовать замену узла.",
        )

    notifications = Notification.objects.order_by("recipient_id")
    recipients = {notification.recipient for notification in notifications}

    assert recipients == {
        notification_setup["specialist_user"],
        notification_setup["superuser"],
    }
    assert notification_setup["requester"] not in recipients
    assert all(notification.metadata["message_type"] == message.message_type for notification in notifications)
    assert all(notification.metadata["visibility"] == message.visibility for notification in notifications)


@pytest.mark.django_db
def test_notification_deduplication_skips_existing_message_notification(notification_setup):
    with _run_on_commit_immediately():
        message = create_public_message(
            notification_setup["order"],
            notification_setup["requester"],
            "Повторно напоминаю о проблеме.",
        )

    initial_count = Notification.objects.count()
    with _run_on_commit_immediately():
        from apps.order_communication.services.notifications import emit_public_message_notifications

        emit_public_message_notifications(message, notification_setup["requester"])

    assert Notification.objects.count() == initial_count
