from django.db import transaction

from apps.orders.models.workflow import OrderWorkflowRule
from apps.orders.services.workflow import get_eligible_specialists_for_order, get_order_workflow_rule


class SupportSpecialistAutoAssigner:
    def __init__(self, instance):
        self.instance = instance

    def assign(self):
        if self.instance.support_specialist_id:
            return self.instance.support_specialist

        with transaction.atomic():
            rule = get_order_workflow_rule(self.instance)
            if not rule or not rule.auto_assign_enabled:
                return None

            available = list(get_eligible_specialists_for_order(self.instance))
            if not available:
                return None

            specialist = self._select_specialist(rule, available)
            self.instance.support_specialist = specialist
            rule.last_assigned_specialist = specialist
            rule.save(update_fields=["last_assigned_specialist"])
            return specialist

    def _select_specialist(self, rule: OrderWorkflowRule, available):
        if rule.assignment_strategy != OrderWorkflowRule.AssignmentStrategy.ROUND_ROBIN:
            return available[0]

        if not rule.last_assigned_specialist_id:
            return available[0]

        available_ids = [specialist.id for specialist in available]
        if rule.last_assigned_specialist_id not in available_ids:
            return available[0]

        last_index = available_ids.index(rule.last_assigned_specialist_id)
        next_index = (last_index + 1) % len(available)
        return available[next_index]
