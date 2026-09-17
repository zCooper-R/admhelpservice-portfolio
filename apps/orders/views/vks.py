from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import CreateView, DetailView, UpdateView

from apps.orders.choices import OrderVKSCategory
from apps.orders.forms import ModalOrderVKSCreateForm, ModalOrderVksUpdateForm
from apps.orders.models.vks import OrderVKS
from apps.orders.services import SupportSpecialistAutoAssigner
from apps.orders.views.mixins import OrderCreateMixin, OrderExecutionAccessMixin, OrderUpdateMixin, OrderTicketDetailQuerysetMixin


class OrderVKSAjaxCreateView(LoginRequiredMixin, OrderCreateMixin, CreateView):
    model = OrderVKS
    form_class = ModalOrderVKSCreateForm
    template_name = 'orders/modal/vks/order_vks_create_ajax.html'

    def pre_save_logic(self, form):
        SupportSpecialistAutoAssigner(form.instance).assign()

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial.update({
            'address': user.get_address(),
            'cabinet': user.get_cabinet(),
            'recipient_email': user.get_email(),
        })
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = OrderVKSCategory
        return context

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


class OrderVKSAjaxDetailView(LoginRequiredMixin, OrderTicketDetailQuerysetMixin, DetailView):
    model = OrderVKS
    template_name = 'orders/modal/vks/order_vks_detail_ajax.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = OrderVKSCategory
        return context


class OrderVKSAjaxUpdateView(
    LoginRequiredMixin,
    OrderExecutionAccessMixin,
    OrderUpdateMixin,
    UpdateView,
):
    model = OrderVKS
    form_class = ModalOrderVksUpdateForm
    template_name = 'orders/modal/vks/order_vks_update_ajax.html'
    success_message = 'Статус успешно изменён.'
