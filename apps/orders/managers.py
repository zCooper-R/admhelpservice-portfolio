from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet

from apps.orders.selectors import OrderDataTableSelector
from apps.orders.services.workflow import get_executor_task_queue_filter, get_moderator_content_types_for_user


class OrderManager(models.Manager):
    def create_by_user(self, instance) -> QuerySet:
        return self.create(content_object=instance, owner=instance.owner, updated_by=instance.owner)

    def get_orders_by_title(self, title) -> QuerySet:
        return self.get_queryset().filter(title=title)

    def prefetch_related_all(self) -> QuerySet:
        return self.get_queryset().prefetch_related('content_object', 'owner')

    def prefetch_related_by_user(self, user_id) -> QuerySet:
        return self.get_queryset().filter(owner=user_id).prefetch_related('content_object', 'owner')

    def prefetch_related_by_content_type(self, ct) -> QuerySet:
        return self.get_queryset().filter(content_type=ct).prefetch_related('content_object', 'owner')

    def _moderator_content_types(self, user):
        return get_moderator_content_types_for_user(user)

    def queryset_my_orders(self, user) -> QuerySet:
        return (
            self.get_queryset()
            .filter(owner=user)
            .select_related('content_type', 'owner')
            .order_by('-created_at')
        )

    def queryset_moderator_tasks(self, user) -> QuerySet:
        qs = self.get_queryset().select_related('content_type', 'owner')
        if user.is_superuser:
            return qs.order_by('-created_at')

        allowed_content_types = self._moderator_content_types(user)
        executor_filter = get_executor_task_queue_filter(user)

        query = Q()
        if allowed_content_types:
            query |= Q(content_type__in=allowed_content_types)
        query |= executor_filter

        if not query:
            return qs.none()

        return qs.filter(query).distinct().order_by('-created_at')

    def to_annotated_list(self, user, *, scope: str = 'tasks') -> list:
        if scope == 'mine':
            orders = list(self.queryset_my_orders(user))
        else:
            if user.is_superuser:
                orders = list(self.prefetch_related_all())
            else:
                orders = list(self.queryset_moderator_tasks(user))

        return OrderDataTableSelector.build_rows(orders, user=user)

    def datatable_page(
        self,
        user,
        *,
        scope: str,
        start: int,
        length: int,
        search_value: str,
        sla_filter: str = 'all',
        order_column: str,
        order_dir: str,
    ) -> tuple:
        if scope == 'mine':
            base_qs = self.queryset_my_orders(user)
        else:
            base_qs = self.queryset_moderator_tasks(user)

        records_total = base_qs.count()

        return OrderDataTableSelector.build_page(
            base_qs,
            user=user,
            records_total=records_total,
            start=start,
            length=length,
            search_value=search_value,
            sla_filter=sla_filter,
            order_column=order_column,
            order_dir=order_dir,
        )
