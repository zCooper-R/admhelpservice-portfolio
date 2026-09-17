import time

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView

from apps.orders.forms import ModalOrderAhoCreateForm, ModalOrderAhoUpdateForm
from apps.orders.models.aho import OrderAho
from apps.orders.services.assignment import SupportSpecialistAutoAssigner
from apps.orders.views.mixins import (
    OrderCreateMixin,
    AjaxViewMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    OrderTicketDetailQuerysetMixin,
)


class OrderAhoAjaxCreateView(LoginRequiredMixin, OrderCreateMixin, CreateView):
    model = OrderAho
    form_class = ModalOrderAhoCreateForm
    template_name = 'orders/modal/aho/order_aho_create_ajax.html'
    # success_message = 'Заявка в Административно-хозяйственный отдел успешно создана!'
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


class OrderAhoAjaxDetailView(LoginRequiredMixin, OrderTicketDetailQuerysetMixin, DetailView):
    model = OrderAho
    template_name = 'orders/modal/aho/order_aho_detail_ajax.html'


class OrderAhoAjaxUpdateView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    UpdateView,
):
    model = OrderAho
    form_class = ModalOrderAhoUpdateForm
    template_name = 'orders/modal/aho/order_aho_update_ajax.html'
    success_message = 'Статус успешно изменён'
