from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import CreateView, DetailView, UpdateView

from apps.orders.choices import OrderStatus
from apps.orders.forms import ModalOrderAccountCreateForm, ModalOrderAccountUpdateForm
from apps.orders.models.account import OrderAccount
from apps.orders.services.assignment import SupportSpecialistAutoAssigner
from apps.orders.tasks import task_mail_protection_sector
from apps.orders.views.mixins import (
    OrderCreateMixin,
    OrderExecutionAccessMixin,
    OrderTicketDetailQuerysetMixin,
    OrderUpdateMixin,
)


class OrderAccountAjaxCreateView(LoginRequiredMixin, OrderCreateMixin, CreateView):
    model = OrderAccount
    form_class = ModalOrderAccountCreateForm
    template_name = 'orders/modal/account/order_account_create_ajax.html'
    def get_initial(self):
        user = self.request.user
        category = self.request.GET.get('category') or self.request.POST.get('category')
        client = user.get_last_name_with_initials() if user.full_name else user

        return {
            'departament': user.get_departament(),
            'category': category,
            'client': client,
            'phone': user.get_phone(),
        }

    def pre_save_logic(self, form):
        SupportSpecialistAutoAssigner(form.instance).assign()
        if form.instance.is_sedo_category:
            form.instance.status = OrderStatus.IN_WORK

    def post_save_logic(self, form, obj):
        if not settings.DEBUG and (obj.is_sedo_category or obj.is_information_systems_category):
            transaction.on_commit(lambda: task_mail_protection_sector.apply_async(args=[obj.id]))

    def form_valid(self, form):
        super().form_valid(form)
        messages_html = render_to_string('orders/messages.html', request=self.request)
        return JsonResponse({
            'success': True,
            'messages_html': messages_html,
        })

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)


class OrderAccountAjaxDetailView(LoginRequiredMixin, OrderTicketDetailQuerysetMixin, DetailView):
    model = OrderAccount
    template_name = 'orders/modal/account/order_account_detail_ajax.html'


class OrderAccountAjaxUpdateView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    UpdateView,
):
    model = OrderAccount
    form_class = ModalOrderAccountUpdateForm
    template_name = 'orders/modal/account/order_account_update_ajax.html'
    success_message = 'Статус успешно изменён'
