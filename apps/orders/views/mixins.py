import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy

from apps.notifications.services import emit_order_created_notification, emit_order_updated_notifications
from apps.order_communication.services.timeline import emit_order_created_timeline_event, emit_order_lifecycle_events
from apps.orders.models.base import Order
from apps.orders.services.waiting import sync_waiting_for_order_object
from apps.orders.services.workflow import user_can_update_order
from apps.orders.tasks import task_mail_admins
from apps.orders.utils.datatables import build_waiting_payload
from utils.logging_audit import log_audit


logger = logging.getLogger('adm.apps.orders')


class OrderTicketDetailQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        if user.has_perm(f'orders.view_{self.model._meta.model_name}') or user.has_perm(f'orders.change_{self.model._meta.model_name}'):
            return qs
        return qs.filter(owner=user) | qs.filter(support_specialist__user=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("object") is not None:
            context["can_update_order"] = user_can_update_order(self.request.user, context["object"])
            wrapper_order = (
                Order.objects.select_related("owner", "updated_by", "content_type")
                .filter(
                    content_type=ContentType.objects.get_for_model(context["object"], for_concrete_model=False),
                    object_id=context["object"].pk,
                )
                .first()
            )
            context["wrapper_order"] = wrapper_order
            if wrapper_order is not None:
                context["waiting_info"] = build_waiting_payload(wrapper_order)
                from apps.order_communication.views.thread import build_thread_context

                context.update(build_thread_context(wrapper_order, self.request.user))
        return context


class AjaxViewMixin:
    @staticmethod
    def is_ajax(request):
        return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


class OrderExecutionAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return user_can_update_order(self.request.user, self.get_object())


class OrderCreateMixin(SuccessMessageMixin):
    success_message = 'Заявка успешно создана.'
    success_url = reverse_lazy('orders:orders_list')

    def pre_save_logic(self, form):
        pass

    def post_save_logic(self, form, obj):
        pass

    def get_success_message(self, cleaned_data=None):
        object_name = getattr(self.object, 'get_category_display_name', lambda: self.object.__class__._meta.verbose_name.title())()
        return f'Заявка #{self.object.id} создана. Категория: {object_name}.'

    def form_valid(self, form):
        form.instance.owner = self.request.user

        self.pre_save_logic(form)
        self.object = form.save()
        self.post_save_logic(form, self.object)
        logger.info(
            'order created model=%s id=%s owner_id=%s',
            self.object._meta.model_name,
            self.object.id,
            self.request.user.pk,
            extra={'event': 'order_created'},
        )
        emit_order_created_timeline_event(self.object, actor=self.request.user)
        emit_order_created_notification(self.object, actor=self.request.user)
        log_audit(
            action='order.create',
            actor=self.request.user,
            entity=self.object._meta.label_lower,
            entity_id=self.object.id,
        )

        if not settings.DEBUG:
            ct = ContentType.objects.get_for_model(self.object)
            obj_id = self.object.id

            def _enqueue_admin_mail(content_type_id=ct.id, object_id=obj_id):
                try:
                    wrapper_order = Order.objects.filter(
                        content_type_id=content_type_id,
                        object_id=object_id,
                    ).only('id').first()
                    if wrapper_order is None:
                        logger.warning(
                            'mail_admins enqueue skipped: wrapper Order not found (ct_id=%s, object_id=%s)',
                            content_type_id,
                            object_id,
                        )
                        return

                    logger.info(
                        'mail_admins enqueue: wrapper Order id=%s (ct_id=%s, object_id=%s)',
                        wrapper_order.id,
                        content_type_id,
                        object_id,
                    )
                    task_mail_admins.delay(wrapper_order.id)
                except Exception:
                    logger.exception(
                        'mail_admins enqueue failed (ct_id=%s, object_id=%s)',
                        content_type_id,
                        object_id,
                    )

            transaction.on_commit(_enqueue_admin_mail)
        super().form_valid(form)

    def get_initial(self):
        user = self.request.user
        client_name = user.get_last_name_with_initials() if user.full_name else user
        return {
            'client': client_name,
            'departament': user.get_departament(),
            'phone': user.get_phone(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not context.get('form'):
            context['form'] = self.get_form_class()(initial=self.get_initial())
        return context


class OrderUpdateMixin:
    update_success_message = 'Изменения сохранены.'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop('request', None)
        return kwargs

    def get_success_message(self):
        details = getattr(self, 'update_success_message', None) or getattr(self, 'success_message', None) or 'Изменения сохранены.'
        return f'Заявка #{self.object.id} обновлена. {details}'.strip()

    def add_success_message(self, message):
        if hasattr(self.request, "_messages"):
            messages.success(self.request, message)

    def form_valid(self, form):
        tracked_instance = form.instance
        changed_fields = tracked_instance.track_changes(exclude_fields=['updated_at']) if hasattr(tracked_instance, 'track_changes') else {}
        self.object = form.save()

        wrapper_order = Order.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.id,
        ).first()
        if wrapper_order is not None:
            wrapper_order.updated_by = self.request.user
            wrapper_order.save(update_fields=['updated_by', 'updated_at'])

        logger.info(
            'order updated model=%s id=%s updated_by=%s changed_fields=%s',
            self.object._meta.model_name,
            self.object.id,
            self.request.user.pk,
            ','.join(sorted(changed_fields)) if changed_fields else '-',
            extra={'event': 'order_updated'},
        )
        sync_waiting_for_order_object(self.object, changed_fields=changed_fields)
        emit_order_lifecycle_events(self.object, actor=self.request.user, changed_fields=changed_fields)
        emit_order_updated_notifications(
            self.object,
            actor=self.request.user,
            changed_fields=changed_fields,
        )
        log_audit(
            action='order.update',
            actor=self.request.user,
            entity=self.object._meta.label_lower,
            entity_id=self.object.id,
            extra={'changed_fields': ','.join(sorted(changed_fields)) if changed_fields else '-'},
        )

        self.add_success_message(self.get_success_message())

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
