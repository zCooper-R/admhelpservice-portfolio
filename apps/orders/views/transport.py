from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from apps.orders.forms import ModalOrderTransportCreateForm, ModalOrderTransportUpdateForm, OrderTransportUpdateForm
from apps.orders.models.transport import OrderTransport
from apps.orders.services.assignment import SupportSpecialistAutoAssigner
from apps.orders.tasks import task_notification_user
from apps.orders.views.mixins import (
    AjaxViewMixin,
    OrderCreateMixin,
    OrderExecutionAccessMixin,
    OrderTicketDetailQuerysetMixin,
    OrderUpdateMixin,
)


class OrderTransportAjaxCreateView(LoginRequiredMixin, OrderCreateMixin, CreateView):
    model = OrderTransport
    form_class = ModalOrderTransportCreateForm
    template_name = 'orders/modal/transport/order_transport_create_ajax.html'
    success_message = 'Отправлено специалисту по транспортному обеспечению.'
    def pre_save_logic(self, form):
        addresses = [address.strip() for address in self.request.POST.getlist('address') if address.strip()]
        if addresses:
            form.instance.address = ' -> '.join(addresses)

        comeback_datetime = self.request.POST.get('comeback_datetime')
        if comeback_datetime:
            form.instance.comeback_datetime = comeback_datetime

        SupportSpecialistAutoAssigner(form.instance).assign()

    def form_valid(self, form):
        super().form_valid(form)
        messages_html = render_to_string("orders/messages.html", request=self.request)
        return JsonResponse({
            'success': True,
            'messages_html': messages_html,
        })

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)


class NotifyTransportUserView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Уведомление создателя заявки на транспорт через Celery.
    Только POST + CSRF + право на изменение транспортной заявки.
    """

    permission_required = 'orders.change_ordertransport'

    def post(self, request, pk):
        transport = get_object_or_404(OrderTransport, pk=pk)
        if not settings.DEBUG:
            task_notification_user.delay(transport_id=transport.id)
        return JsonResponse({'status': 'ok'})


class OrderTransportAjaxDetailView(LoginRequiredMixin, OrderTicketDetailQuerysetMixin, DetailView):
    model = OrderTransport
    template_name = 'orders/modal/transport/order_transport_detail_ajax.html'

    def get_queryset(self):
        return super().get_queryset().select_related('driver', 'driver__car')


class OrderTransportAjaxUpdateView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    UpdateView,
):
    model = OrderTransport
    form_class = ModalOrderTransportUpdateForm
    template_name = 'orders/modal/transport/order_transport_update_ajax.html'
    success_message = 'Заявка успешно изменена'
    def get_form_class(self):
        if not AjaxViewMixin.is_ajax(self.request):
            return OrderTransportUpdateForm
        return super().get_form_class()
