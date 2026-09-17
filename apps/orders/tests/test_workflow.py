import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from apps.orders.choices import OrderPrinterCategory, OrderStatus
from apps.orders.models import OrderPrinter, OrderWorkflowRule
from apps.orders.services.assignment import SupportSpecialistAutoAssigner
from apps.orders.services.workflow import (
    get_eligible_specialists_for_order,
    get_moderators_for_order,
    get_order_workflow_rule,
    user_can_execute_order,
    user_can_moderate_order,
)
from apps.users.models import SupportSpecialist, TechnicalGroup


def create_user(username: str):
    return get_user_model().objects.create_user(username=username, password="pass", full_name=username)


def create_moderator_group(name: str = "adm_moderator_orderprinter"):
    return Group.objects.create(name=name)


def create_specialist(username: str, *, technical_group=None, is_available=True, is_active=True):
    user = create_user(username)
    user.is_active = is_active
    user.save(update_fields=["is_active"])
    specialist = SupportSpecialist.objects.create(
        user=user,
        technical_group=technical_group,
        is_available=is_available,
    )
    return user, specialist


def create_order(owner, *, specialist=None):
    return OrderPrinter.objects.create(
        owner=owner,
        support_specialist=specialist,
        client="Тест",
        address="Адрес",
        departament="Отдел",
        cabinet="101",
        phone="123",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
        description="Описание",
    )


def create_workflow_rule(*, moderator_groups=None, eligible_specialists=None, technical_group=None):
    rule = OrderWorkflowRule.objects.create(
        content_type=ContentType.objects.get_for_model(OrderPrinter),
        technical_group=technical_group,
        auto_assign_enabled=True,
    )
    if moderator_groups:
        rule.moderator_groups.set(moderator_groups)
    if eligible_specialists:
        rule.eligible_specialists.set(eligible_specialists)
    return rule


@pytest.mark.django_db
def test_moderator_resolution_uses_explicit_workflow_groups_not_change_permission():
    owner = create_user("owner_perm")
    moderator_group = create_moderator_group()
    moderator = create_user("moderator_group_user")
    moderator.groups.add(moderator_group)
    permission_only = create_user("permission_only_user")
    permission_only.user_permissions.add(Permission.objects.get(codename="change_orderprinter"))
    create_workflow_rule(moderator_groups=[moderator_group])
    order = create_order(owner)

    moderators = list(get_moderators_for_order(order))

    assert moderators == [moderator]
    assert permission_only not in moderators


@pytest.mark.django_db
def test_workflow_rule_stores_explicit_specialist_pool():
    owner = create_user("owner_rule")
    technical_group = TechnicalGroup.objects.create(name="Printer line", priority=TechnicalGroup.Priority.HIGH)
    _, specialist = create_specialist("printer_exec", technical_group=technical_group)
    create_workflow_rule(eligible_specialists=[specialist], technical_group=technical_group)
    order = create_order(owner)

    rule = get_order_workflow_rule(order)

    assert list(get_eligible_specialists_for_order(order)) == [specialist]
    assert rule.technical_group == technical_group


@pytest.mark.django_db
def test_auto_assign_uses_only_explicit_specialist_pool():
    owner = create_user("owner_auto_assign")
    technical_group = TechnicalGroup.objects.create(name="Printer line", priority=TechnicalGroup.Priority.HIGH)
    other_group = TechnicalGroup.objects.create(name="Other line", priority=TechnicalGroup.Priority.MID)
    _, assigned_specialist = create_specialist("printer_exec", technical_group=technical_group)
    create_specialist("other_exec", technical_group=other_group)
    create_workflow_rule(eligible_specialists=[assigned_specialist], technical_group=technical_group)

    order = OrderPrinter(
        owner=owner,
        client="Тест",
        address="Адрес",
        departament="Отдел",
        cabinet="101",
        phone="123",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
        description="Описание",
    )

    specialist = SupportSpecialistAutoAssigner(order).assign()

    assert specialist == assigned_specialist
    assert order.support_specialist == assigned_specialist


@pytest.mark.django_db
def test_auto_assign_excludes_unavailable_and_inactive_specialists():
    owner = create_user("owner_auto_assign_exclusions")
    technical_group = TechnicalGroup.objects.create(name="Printer line", priority=TechnicalGroup.Priority.HIGH)
    create_specialist("unavailable_exec", technical_group=technical_group, is_available=False)
    create_specialist("inactive_exec", technical_group=technical_group, is_active=False)
    _, eligible_specialist = create_specialist("eligible_exec", technical_group=technical_group, is_available=True)
    create_workflow_rule(eligible_specialists=list(SupportSpecialist.objects.all()), technical_group=technical_group)

    order = OrderPrinter(
        owner=owner,
        client="Тест",
        address="Адрес",
        departament="Отдел",
        cabinet="101",
        phone="123",
        printer_name="HP",
        category=OrderPrinterCategory.REPAIR,
        status=OrderStatus.ACCEPTED,
        description="Описание",
    )

    specialist = SupportSpecialistAutoAssigner(order).assign()

    assert specialist == eligible_specialist


@pytest.mark.django_db
def test_assigned_executor_can_open_update_view_without_moderator_permission():
    owner = create_user("owner_update")
    specialist_user, specialist = create_specialist("executor_update")
    order = create_order(owner, specialist=specialist)
    client = Client(HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert client.login(username="executor_update", password="pass")

    response = client.get(reverse("orders:order_printer_update", kwargs={"pk": order.pk}))

    assert response.status_code == 200
    assert user_can_execute_order(specialist_user, order) is True


@pytest.mark.django_db
def test_workflow_moderator_requires_group_and_permission_for_operational_access():
    owner = create_user("owner_moderator_access")
    moderator_group = create_moderator_group()
    moderator = create_user("moderator_access")
    moderator.groups.add(moderator_group)
    moderator.user_permissions.add(Permission.objects.get(codename="change_orderprinter"))
    create_workflow_rule(moderator_groups=[moderator_group])
    order = create_order(owner)

    assert user_can_moderate_order(moderator, order) is True


@pytest.mark.django_db
def test_assigned_executor_sees_order_in_task_queue():
    owner = create_user("owner_queue")
    _, specialist = create_specialist("executor_queue")
    create_order(owner, specialist=specialist)

    client = Client()
    assert client.login(username="executor_queue", password="pass")

    response = client.get(reverse("orders:tasks_list"))

    assert response.status_code == 200
    assert "Задачи на исполнение" in response.content.decode("utf-8")
