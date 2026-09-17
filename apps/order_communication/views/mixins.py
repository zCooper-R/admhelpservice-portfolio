from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from apps.order_communication.services.policies import can_view_thread
from apps.orders.models.base import Order


class OrderCommunicationOrderMixin:
    def get_order(self):
        order = get_object_or_404(Order.objects.select_related("owner", "updated_by", "content_type"), pk=self.kwargs["order_id"])
        if not can_view_thread(self.request.user, order):
            raise PermissionDenied
        return order


class AjaxRequestRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class MessageFormMixin:
    form_class = None

    def get_form_class(self):
        if self.form_class is None:
            raise NotImplementedError("form_class must be defined")
        return self.form_class

    def get_form(self):
        return self.get_form_class()(self.request.POST or None, self.request.FILES or None)
