from collections import defaultdict
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.utils.dateformat import DateFormat

from apps.orders.choices import OrderWaitingFor
from apps.orders.services.sla import get_sla_state, get_time_left


def format_sla_duration(delta):
    if delta is None:
        return ""

    total_seconds = int(abs(delta.total_seconds()))
    if total_seconds < 60:
        return "меньше минуты"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(_pluralize_ru(days, "день", "дня", "дней"))
    if hours:
        parts.append(_pluralize_ru(hours, "час", "часа", "часов"))
    if minutes and not days:
        parts.append(_pluralize_ru(minutes, "минута", "минуты", "минут"))

    return " ".join(parts[:2])


def build_waiting_payload(order):
    label = order.get_waiting_for_display()
    waiting_for = getattr(order, "waiting_for", OrderWaitingFor.NONE)
    if waiting_for == OrderWaitingFor.NONE:
        return {
            "label": label,
            "short_label": "—",
            "variant": "none",
            "sla_state": "ok",
            "detail": "",
        }

    time_left = get_time_left(order)
    is_overdue = time_left is not None and time_left.total_seconds() < 0
    return {
        "label": label,
        "short_label": "Исполнитель" if waiting_for == OrderWaitingFor.EXECUTOR else "Заявитель",
        "variant": waiting_for,
        "sla_state": get_sla_state(order),
        "detail": (
            f"Просрочено на {format_sla_duration(time_left)}"
            if is_overdue
            else f"Осталось: ~{format_sla_duration(time_left)}"
        ),
    }


def _pluralize_ru(value, one, few, many):
    remainder_100 = value % 100
    remainder_10 = value % 10
    if 11 <= remainder_100 <= 14:
        form = many
    elif remainder_10 == 1:
        form = one
    elif 2 <= remainder_10 <= 4:
        form = few
    else:
        form = many
    return f"{value} {form}"


def prefetch_order_content_objects(orders):
    if not orders:
        return
    by_ct_ids = defaultdict(set)
    for order in orders:
        by_ct_ids[order.content_type_id].add(order.object_id)

    cache = {}
    for ct_id, id_set in by_ct_ids.items():
        ct = ContentType.objects.get_for_id(ct_id)
        model = ct.model_class()
        if model is None:
            continue
        queryset = model.objects.filter(pk__in=id_set)
        try:
            model._meta.get_field("support_specialist")
        except FieldDoesNotExist:
            pass
        else:
            queryset = queryset.select_related("support_specialist__user")
        for obj in queryset:
            cache[(ct_id, obj.pk)] = obj

    field = orders[0]._meta.get_field("content_object")
    for order in orders:
        obj = cache.get((order.content_type_id, order.object_id))
        if obj is None:
            continue
        if hasattr(field, "set_cached_value"):
            field.set_cached_value(order, obj)
        else:
            setattr(order, field.cache_name, obj)


class DataTableRowBuilder:
    @classmethod
    def build(cls, order, *, unread_count=0):
        obj = order.content_object
        if obj is None:
            return {
                "order": order,
                "row": {
                    "id": order.id,
                    "category": "-",
                    "client": "-",
                    "executor": "Не назначен",
                    "status": "-",
                    "waiting_for": build_waiting_payload(order),
                    "created_at": cls.format_date(order.created_at),
                    "url": "#",
                    "discussion_unread_count": unread_count,
                },
            }

        row = {
            "id": order.id,
            "category": obj.get_category_display_name(),
            "client": getattr(obj, "client", "-"),
            "executor": cls.get_executor_display(obj),
            "status": getattr(obj, "get_status_display", lambda: "-")(),
            "waiting_for": build_waiting_payload(order),
            "created_at": cls.format_date(getattr(obj, "created_at", order.created_at)),
            "url": obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else "#",
            "discussion_unread_count": unread_count,
        }
        return {"order": order, "row": row}

    @classmethod
    def build_many(cls, orders, *, user=None) -> list:
        prefetch_order_content_objects(orders)
        unread_by_order_id = {}
        if user is not None:
            from apps.order_communication.selectors.unread import get_unread_count_by_order_ids

            unread_by_order_id = get_unread_count_by_order_ids([order.id for order in orders], user)
        return [
            cls.build(order, unread_count=unread_by_order_id.get(order.id, 0))
            for order in orders
        ]

    @staticmethod
    def format_date(dt):
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, "%d.%m.%Y %H:%M")
            except Exception:
                return dt
        return DateFormat(dt).format("d.m.Y H:i")

    @staticmethod
    def get_executor_display(obj):
        specialist = getattr(obj, "support_specialist", None)
        if specialist is None:
            return "Не назначен"
        user = getattr(specialist, "user", None)
        return str(user or specialist)
