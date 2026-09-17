from typing import NamedTuple, Optional, Tuple, Type

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, Q, QuerySet

from apps.orders.models.workflow import OrderWorkflowRule
from apps.users.models import SupportSpecialist


class OrderWorkflowConfig(NamedTuple):
    model_label: str
    change_permission: str
    view_permission: str
    related_query_name: str

    @property
    def model(self):
        app_label, model_name = self.model_label.split(".", 1)
        return apps.get_model(app_label, model_name)


ORDER_WORKFLOW_CONFIGS = (
    OrderWorkflowConfig("orders.OrderPrinter", "orders.change_orderprinter", "orders.view_orderprinter", "orders_printer"),
    OrderWorkflowConfig("orders.OrderTransport", "orders.change_ordertransport", "orders.view_ordertransport", "orders_transport"),
    OrderWorkflowConfig("orders.OrderPC", "orders.change_orderpc", "orders.view_orderpc", "orders_pc"),
    OrderWorkflowConfig("orders.OrderAho", "orders.change_orderaho", "orders.view_orderaho", "orders_aho"),
    OrderWorkflowConfig("orders.OrderVKS", "orders.change_ordervks", "orders.view_ordervks", "orders_vks"),
    OrderWorkflowConfig("orders.OrderAccount", "orders.change_orderaccount", "orders.view_orderaccount", "orders_account"),
)


def get_workflow_configs() -> Tuple[OrderWorkflowConfig, ...]:
    return ORDER_WORKFLOW_CONFIGS


def get_workflow_config_for_model(model: Type) -> OrderWorkflowConfig:
    for config in ORDER_WORKFLOW_CONFIGS:
        if config.model == model:
            return config
    raise KeyError(f"Workflow config is not defined for model {model!r}")


def get_workflow_config_for_instance(order_object) -> OrderWorkflowConfig:
    return get_workflow_config_for_model(order_object.__class__)


def get_executor_task_queue_filter(user) -> Q:
    query = Q()
    for config in ORDER_WORKFLOW_CONFIGS:
        query |= Q(**{f"{config.related_query_name}__support_specialist__user": user})
    return query


def get_order_workflow_rule(order_object) -> Optional[OrderWorkflowRule]:
    content_type = ContentType.objects.get_for_model(order_object, for_concrete_model=False)
    return (
        OrderWorkflowRule.objects.select_related("technical_group", "last_assigned_specialist", "last_assigned_specialist__user")
        .prefetch_related(
            "moderator_groups__user_set",
            Prefetch("eligible_specialists", queryset=SupportSpecialist.objects.select_related("user", "technical_group")),
        )
        .filter(content_type=content_type)
        .first()
    )


def get_workflow_rule_for_model(model: Type) -> Optional[OrderWorkflowRule]:
    content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)
    return (
        OrderWorkflowRule.objects.select_related("technical_group", "last_assigned_specialist", "last_assigned_specialist__user")
        .prefetch_related(
            "moderator_groups__user_set",
            Prefetch("eligible_specialists", queryset=SupportSpecialist.objects.select_related("user", "technical_group")),
        )
        .filter(content_type=content_type)
        .first()
    )


def get_moderator_group_names_for_model(model: Type) -> list:
    rule = get_workflow_rule_for_model(model)
    if rule:
        return list(rule.moderator_groups.values_list("name", flat=True))
    return []


def get_moderator_users_for_model(model: type) -> QuerySet:
    User = apps.get_model("users", "User")
    rule = get_workflow_rule_for_model(model)
    if not rule:
        return User.objects.none()
    return (
        User.objects.filter(is_active=True, groups__order_workflow_rules=rule)
        .distinct()
    )


def get_moderators_for_order(order_object) -> QuerySet:
    return get_moderator_users_for_model(order_object.__class__)


def get_moderator_content_types_for_user(user) -> list:
    if not getattr(user, "is_authenticated", False):
        return []
    if user.is_superuser:
        return [ContentType.objects.get_for_model(config.model) for config in ORDER_WORKFLOW_CONFIGS]

    return [
        ContentType.objects.get_for_model(config.model, for_concrete_model=False)
        for config in ORDER_WORKFLOW_CONFIGS
        if (
            OrderWorkflowRule.objects.filter(
                content_type=ContentType.objects.get_for_model(config.model, for_concrete_model=False),
                moderator_groups__user=user,
            ).exists()
            and user.has_perm(config.change_permission)
        )
    ]


def user_has_workflow_moderator_role(user, order_object) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return bool(
        OrderWorkflowRule.objects.filter(
            content_type=ContentType.objects.get_for_model(order_object, for_concrete_model=False),
            moderator_groups__user=user,
        ).exists()
    )


def user_can_access_task_queue(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    if SupportSpecialist.objects.filter(user=user).exists():
        return True
    return bool(get_moderator_content_types_for_user(user))


def user_can_execute_order(user, order_object) -> bool:
    specialist = getattr(order_object, "support_specialist", None)
    return bool(user and specialist and getattr(specialist, "user", None) == user)


def user_can_moderate_order(user, order_object) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    config = get_workflow_config_for_instance(order_object)
    return user_has_workflow_moderator_role(user, order_object) and user.has_perm(config.change_permission)


def user_can_view_order(user, order_object) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user == getattr(order_object, "owner", None):
        return True
    if user_can_execute_order(user, order_object):
        return True
    if user.is_superuser:
        return True
    config = get_workflow_config_for_instance(order_object)
    return user.has_perm(config.view_permission) or user_can_moderate_order(user, order_object)


def user_can_update_order(user, order_object) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user_can_execute_order(user, order_object) or user_can_moderate_order(user, order_object)


def get_eligible_specialists_for_order(order_object):
    rule = get_order_workflow_rule(order_object)
    if not rule:
        return SupportSpecialist.objects.none()
    return (
        rule.eligible_specialists.filter(is_available=True, user__is_active=True)
        .select_related("user", "technical_group")
        .order_by("id")
    )
