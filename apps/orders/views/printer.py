from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.order_communication.services.timeline import emit_order_lifecycle_events
from apps.orders.choices import OrderStatus
from apps.orders.forms import ModalOrderPrinterCreateForm, ModalOrderPrinterUpdateForm
from apps.orders.models.printer import OrderPrinter
from apps.orders.services.assignment import SupportSpecialistAutoAssigner
from apps.orders.services.waiting import sync_waiting_for_order_object
from apps.orders.tasks import task_mail_organisation, task_mail_organisation_from_admin_panel
from apps.orders.views.mixins import (
    OrderCreateMixin,
    AjaxViewMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    OrderTicketDetailQuerysetMixin,
)



class OrderPrinterAjaxCreateView(LoginRequiredMixin, OrderCreateMixin, CreateView):
    model = OrderPrinter
    form_class = ModalOrderPrinterCreateForm
    template_name = 'orders/modal/printer/order_printer_create_ajax.html'
    def pre_save_logic(self, form):
        if form.instance.is_refill_category():
            form.instance.status = OrderStatus.IN_WORK
            return
        SupportSpecialistAutoAssigner(form.instance).assign()

    def post_save_logic(self, form, obj):
        if not settings.DEBUG and obj and obj.is_refill_category():
            transaction.on_commit(lambda: task_mail_organisation.apply_async(args=[obj.id]))

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


class OrderPrinterAjaxDetailView(LoginRequiredMixin, OrderTicketDetailQuerysetMixin, DetailView):
    model = OrderPrinter
    template_name = 'orders/modal/printer/order_printer_detail_ajax.html'


class OrderPrinterSendToTechnoServiceConfirmView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    SingleObjectMixin,
    View,
):
    model = OrderPrinter
    template_name = 'orders/modal/_confirm_action_modal.html'

    def get(self, request, *args, **kwargs):
        order = self.get_object()
        context = {
            'modal_title': f'Техно-Сервис для заявки #{order.pk}',
            'modal_kicker': 'Подтверждение',
            'modal_heading': 'Отправка во внешнюю организацию',
            'modal_message': 'Заявка будет отправлена в Техно-Сервис на обслуживание принтера.',
            'modal_hint': 'После отправки заявка будет отмечена как переданная, а статус переключится в "В работе".',
            'confirm_post_url': reverse_lazy('orders:order_printer_send_to_techno_service', kwargs={'pk': order.pk}),
            'confirm_button_text': 'Отправить',
            'confirm_button_icon': 'fas fa-envelope',
            'confirm_button_class': 'btn-primary',
            'confirm_success_message': 'Заявка отправлена в Техно-Сервис.',
            'back_url': order.get_absolute_url(),
        }
        return render(request, self.template_name, context)


class OrderPrinterSendToTechnoServiceView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    SingleObjectMixin,
    View,
):
    model = OrderPrinter

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        previous_status = order.status

        if order.emailed_to_organisation:
            messages.info(request, 'Заявка уже была отправлена в Техно-Сервис.')
        elif settings.DEBUG:
            messages.warning(request, 'В режиме DEBUG отправка уведомлений отключена.')
        else:
            task_mail_organisation_from_admin_panel.delay(order.id)
            order.status = OrderStatus.IN_WORK
            order.emailed_to_organisation = True
            order.save(update_fields=['status', 'emailed_to_organisation', 'updated_at'])
            sync_waiting_for_order_object(order, changed_fields={"status": (previous_status, order.status)})
            emit_order_lifecycle_events(
                order,
                actor=request.user,
                changed_fields={"status": (previous_status, order.status)},
            )
            messages.success(request, 'Заявка отправлена в Техно-Сервис.')

        messages_html = render_to_string("orders/messages.html", request=request)
        return JsonResponse(
            {
                'success': True,
                'messages_html': messages_html,
                'detail_url': order.get_absolute_url(),
            }
        )


class OrderPrinterAjaxUpdateView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    UpdateView,
):
    model = OrderPrinter
    form_class = ModalOrderPrinterUpdateForm
    template_name = 'orders/modal/printer/order_printer_update_ajax.html'
    success_message = 'Заявка успешно изменена'
