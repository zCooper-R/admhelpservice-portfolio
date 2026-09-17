from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from apps.notifications.views import get_notification_summary_payload
from apps.order_communication.selectors.unread import get_unread_count_by_order_ids
from apps.orders.models.base import Order
from apps.orders.selectors import OrderDataTableSelector
from apps.orders.services.workflow import user_can_access_task_queue
from apps.orders.utils.datatables import build_waiting_payload, prefetch_order_content_objects


class AjaxOrdersListView(LoginRequiredMixin, View):
    """Список заявок текущего пользователя."""

    template_name = "orders/my_orders.html"
    datatable_scope = "mine"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 10))
        search_value = request.POST.get("search[value]", "").strip()
        sla_filter = OrderDataTableSelector.normalize_sla_filter(request.POST.get("sla_filter"))
        order_column_index = request.POST.get("order[0][column]", 0)
        order_column_name = request.POST.get(f"columns[{order_column_index}][data]", "created_at")
        order_dir = request.POST.get("order[0][dir]", "desc")

        records_total, records_filtered, data = Order.objects.datatable_page(
            request.user,
            scope=self.datatable_scope,
            start=start,
            length=length,
            search_value=search_value,
            sla_filter=sla_filter,
            order_column=order_column_name,
            order_dir=order_dir,
        )
        return JsonResponse(
            {
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": data,
            }
        )


class AjaxTasksListView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Список рабочих заявок для модераторов и назначенных исполнителей."""

    template_name = "orders/tasks_list.html"
    datatable_scope = "tasks"

    def test_func(self):
        return user_can_access_task_queue(self.request.user)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 10))
        search_value = request.POST.get("search[value]", "").strip()
        sla_filter = OrderDataTableSelector.normalize_sla_filter(request.POST.get("sla_filter"))
        order_column_index = request.POST.get("order[0][column]", 0)
        order_column_name = request.POST.get(f"columns[{order_column_index}][data]", "created_at")
        order_dir = request.POST.get("order[0][dir]", "desc")

        records_total, records_filtered, data = Order.objects.datatable_page(
            request.user,
            scope=self.datatable_scope,
            start=start,
            length=length,
            search_value=search_value,
            sla_filter=sla_filter,
            order_column=order_column_name,
            order_dir=order_dir,
        )
        return JsonResponse(
            {
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": data,
            }
        )


class GlobalUiSummaryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        raw_order_ids = request.GET.getlist("order_ids")
        order_ids = []
        for value in raw_order_ids:
            try:
                order_ids.append(int(value))
            except (TypeError, ValueError):
                continue

        unique_order_ids = list(dict.fromkeys(order_ids))
        orders = list(Order.objects.filter(pk__in=unique_order_ids).select_related("content_type"))
        prefetch_order_content_objects(orders)
        statuses = {
            str(order.id): (
                getattr(order.content_object, "get_status_display", lambda: "-")()
                if order.content_object is not None
                else "-"
            )
            for order in orders
        }
        waiting = {
            str(order.id): build_waiting_payload(order)
            for order in orders
        }
        return JsonResponse(
            {
                "notifications": get_notification_summary_payload(request.user),
                "discussion": {
                    "counts": get_unread_count_by_order_ids(unique_order_ids, request.user),
                },
                "orders": {
                    "statuses": statuses,
                    "waiting": waiting,
                },
            }
        )
