import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from apps.orders.choices import OrderPrinterCategory, OrderStatus
from apps.orders.models import Order, OrderPrinter, OrderWorkflowRule
from apps.orders.services.workflow import get_moderator_content_types_for_user
from apps.users.models import SupportSpecialist


def create_user(username: str):
    return get_user_model().objects.create_user(username=username, password="pass", full_name=username)


def create_moderator_group(name: str = "adm_moderator_orderprinter"):
    return Group.objects.create(name=name)


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


def create_workflow_rule(*, moderator_groups=None):
    rule = OrderWorkflowRule.objects.create(
        content_type=ContentType.objects.get_for_model(OrderPrinter),
        auto_assign_enabled=True,
    )
    if moderator_groups:
        rule.moderator_groups.set(moderator_groups)
    return rule


@pytest.mark.django_db
def test_support_specialist_without_moderator_permission_sees_only_assigned_tasks():
    owner = create_user("owner_executor_scope")
    specialist_user, specialist = create_specialist("executor_scope")
    create_workflow_rule()
    assigned_order = create_order(owner, specialist=specialist)
    foreign_order = create_order(owner)

    task_ids = list(Order.objects.queryset_moderator_tasks(specialist_user).values_list("object_id", flat=True))

    assert task_ids == [assigned_order.id]
    assert foreign_order.id not in task_ids


@pytest.mark.django_db
def test_workflow_moderator_with_change_permission_sees_category_queue():
    owner = create_user("owner_moderator_scope")
    moderator_group = create_moderator_group()
    moderator = create_user("moderator_scope")
    moderator.groups.add(moderator_group)
    moderator.user_permissions.add(Permission.objects.get(codename="change_orderprinter"))
    create_workflow_rule(moderator_groups=[moderator_group])
    order = create_order(owner)

    content_types = get_moderator_content_types_for_user(moderator)
    task_ids = list(Order.objects.queryset_moderator_tasks(moderator).values_list("object_id", flat=True))

    assert ContentType.objects.get_for_model(OrderPrinter) in content_types
    assert order.id in task_ids
