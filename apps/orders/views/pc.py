from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from django.views.generic import CreateView, DetailView, UpdateView

from apps.orders.forms import ModalOrderPcCreateForm, ModalOrderPcUpdateForm
from apps.orders.models import OrderPC
from apps.orders.services.assignment import SupportSpecialistAutoAssigner
from apps.orders.views.mixins import (
    OrderCreateMixin,
    AjaxViewMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    OrderTicketDetailQuerysetMixin,
)


class OrderPCAjaxCreateView(LoginRequiredMixin, OrderCreateMixin, CreateView):
    model = OrderPC
    form_class = ModalOrderPcCreateForm
    template_name = 'orders/modal/pc/order_pc_create_ajax.html'
    def pre_save_logic(self, form):
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


class OrderPCAjaxDetailView(LoginRequiredMixin, OrderTicketDetailQuerysetMixin, DetailView):
    model = OrderPC
    template_name = 'orders/modal/pc/order_pc_detail_ajax.html'


class OrderPCAjaxUpdateView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    UpdateView,
):
    model = OrderPC
    form_class = ModalOrderPcUpdateForm
    template_name = 'orders/modal/pc/order_pc_update_ajax.html'
    success_message = 'Статус успешно изменён'
