from django.db.models import Q
from django.utils import timezone

from apps.orders.choices import OrderWaitingFor
from apps.orders.services.sla import (
    EXECUTOR_RESPONSE_TIMEOUT,
    REQUESTER_RESPONSE_TIMEOUT,
    WARNING_THRESHOLD,
)
from apps.orders.services.workflow import get_workflow_configs
from apps.orders.utils.datatables import DataTableRowBuilder


class OrderDataTableSelector:
    PYTHON_SORT_COLUMNS = {'category', 'client', 'status'}
    SLA_FILTER_VALUES = {'all', 'overdue', 'warning', 'none'}

    @classmethod
    def build_rows(cls, orders, *, user=None):
        return DataTableRowBuilder.build_many(orders, user=user)

    @classmethod
    def build_page(
        cls,
        qs,
        *,
        user,
        records_total,
        start,
        length,
        search_value,
        sla_filter,
        order_column,
        order_dir,
    ):
        order_column = order_column or 'created_at'
        order_dir = (order_dir or 'desc').lower()
        prefix = '-' if order_dir == 'desc' else ''
        search_value = (search_value or '').strip()
        sla_filter = cls.normalize_sla_filter(sla_filter)

        qs = cls.apply_sla_filter(qs, sla_filter)
        qs = cls.apply_search_filter(qs, search_value)
        records_filtered = qs.count()

        if sla_filter != 'all':
            rows = cls.build_rows(list(qs), user=user)
            rows.sort(
                key=lambda item: cls.get_sort_key(item, order_column),
                reverse=order_dir == 'desc',
            )
            page_rows = rows[start : start + length]
            return records_total, records_filtered, [r['row'] for r in page_rows]

        if search_value:
            rows = cls.build_rows(list(qs), user=user)
            rows.sort(
                key=lambda item: cls.get_sort_key(item, order_column),
                reverse=order_dir == 'desc',
            )
            page_rows = rows[start : start + length]
            return records_total, records_filtered, [r['row'] for r in page_rows]

        if order_column == 'id':
            page_orders = list(qs.order_by(f'{prefix}id')[start : start + length])
            rows = cls.build_rows(page_orders, user=user)
            return records_total, records_filtered, [r['row'] for r in rows]

        if order_column == 'created_at':
            page_orders = list(qs.order_by(f'{prefix}created_at')[start : start + length])
            rows = cls.build_rows(page_orders, user=user)
            return records_total, records_filtered, [r['row'] for r in rows]

        if order_column == 'waiting_for':
            page_orders = list(
                qs.order_by(f'{prefix}waiting_for', f'{prefix}waiting_since')[start : start + length]
            )
            rows = cls.build_rows(page_orders, user=user)
            return records_total, records_filtered, [r['row'] for r in rows]

        if order_column in cls.PYTHON_SORT_COLUMNS:
            rows = cls.build_rows(list(qs), user=user)
            rows.sort(
                key=lambda item: cls.normalize_sort_value(item['row'].get(order_column)),
                reverse=order_dir == 'desc',
            )
            page_rows = rows[start : start + length]
            return records_total, records_filtered, [r['row'] for r in page_rows]

        page_orders = list(qs.order_by('-created_at')[start : start + length])
        rows = cls.build_rows(page_orders, user=user)
        return records_total, records_filtered, [r['row'] for r in rows]

    @classmethod
    def normalize_sla_filter(cls, value):
        value = (value or 'all').strip().lower()
        return value if value in cls.SLA_FILTER_VALUES else 'all'

    @classmethod
    def apply_sla_filter(cls, qs, sla_filter):
        if sla_filter == 'all':
            return qs
        if sla_filter == 'none':
            return qs.filter(waiting_for=OrderWaitingFor.NONE)

        now = timezone.now()
        executor_overdue_from = now - EXECUTOR_RESPONSE_TIMEOUT
        requester_overdue_from = now - REQUESTER_RESPONSE_TIMEOUT
        executor_warning_from = now - EXECUTOR_RESPONSE_TIMEOUT * (1 - WARNING_THRESHOLD)
        requester_warning_from = now - REQUESTER_RESPONSE_TIMEOUT * (1 - WARNING_THRESHOLD)

        if sla_filter == 'overdue':
            return qs.filter(
                Q(waiting_for=OrderWaitingFor.EXECUTOR, waiting_since__lte=executor_overdue_from)
                | Q(waiting_for=OrderWaitingFor.REQUESTER, waiting_since__lte=requester_overdue_from)
            )
        if sla_filter == 'warning':
            return qs.filter(
                Q(
                    waiting_for=OrderWaitingFor.EXECUTOR,
                    waiting_since__gt=executor_overdue_from,
                    waiting_since__lte=executor_warning_from,
                )
                | Q(
                    waiting_for=OrderWaitingFor.REQUESTER,
                    waiting_since__gt=requester_overdue_from,
                    waiting_since__lte=requester_warning_from,
                )
            )
        return qs

    @classmethod
    def apply_search_filter(cls, qs, search_value):
        needle = cls.normalize_sort_value(search_value)
        if not needle:
            return qs

        query = Q()
        waiting_values = [
            value
            for value, label in OrderWaitingFor.choices
            if needle in label.casefold() or needle in value.casefold()
        ]
        if waiting_values:
            query |= Q(waiting_for__in=waiting_values)

        for config in get_workflow_configs():
            related_name = config.related_query_name
            model = config.model
            query |= cls.build_related_text_search_query(model, related_name, 'client', search_value)
            query |= cls.build_related_choice_search_query(model, related_name, 'status', search_value)
            query |= cls.build_related_choice_search_query(model, related_name, 'category', search_value)
            query |= cls.build_related_text_search_query(model, related_name, 'transport_city', search_value)

        return qs.filter(query).distinct()

    @classmethod
    def build_related_choice_search_query(cls, model, related_name, field_name, search_value):
        try:
            field = model._meta.get_field(field_name)
        except Exception:
            return Q()

        needle = cls.normalize_sort_value(search_value)
        values = [
            value
            for value, label in field.choices
            if needle in str(label).casefold() or needle in str(value).casefold()
        ]
        if not values:
            return Q()
        return Q(**{f'{related_name}__{field_name}__in': values})

    @staticmethod
    def build_related_text_search_query(model, related_name, field_name, search_value):
        try:
            model._meta.get_field(field_name)
        except Exception:
            return Q()

        query = Q(**{f'{related_name}__{field_name}__icontains': search_value})
        for variant in {
            search_value,
            search_value.lower(),
            search_value.upper(),
            search_value.capitalize(),
            search_value.title(),
        }:
            query |= Q(**{f'{related_name}__{field_name}__contains': variant})
        return query

    @staticmethod
    def normalize_sort_value(value):
        if value is None:
            return ''
        if isinstance(value, dict):
            value = value.get('label') or value.get('detail') or ''
        if isinstance(value, str):
            return value.casefold()
        return value

    @classmethod
    def get_sort_key(cls, item, order_column):
        if order_column == 'id':
            return item['row'].get('id', 0)
        if order_column == 'created_at':
            return getattr(item['order'], 'created_at', None)
        return cls.normalize_sort_value(item['row'].get(order_column))
