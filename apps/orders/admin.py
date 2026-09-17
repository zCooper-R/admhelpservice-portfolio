import json
import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.models import LogEntry, DELETION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms import Field
from django.template.defaultfilters import urlencode
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from rangefilter import filters

from apps.notifications.services import emit_order_updated_notifications
from apps.order_communication.services.timeline import emit_order_lifecycle_events
from apps.orders.choices import OrderStatus
from apps.orders.services.waiting import sync_waiting_for_order_object


import csv
from django.http import HttpResponse

from apps.users.model_managers import SupportSpecialistManager
from apps.users.models import SupportSpecialist
from apps.orders.models.account import OrderAccount
from apps.orders.models.aho import OrderAho
from apps.orders.models.base import Order
from apps.orders.models.feedback import Feedback
from apps.orders.models.pc import OrderPC
from apps.orders.models.printer import OrderPrinter
from apps.orders.models.transport import OrderTransport
from apps.orders.models.vks import OrderVKS
from apps.orders.models.workflow import OrderWorkflowRule

logger = logging.getLogger('adm.audit')


class ExportCsvMixin:
    """
    A mixin to add an "Export to CSV" button to the admin site.
    """

    def export_to_csv(self, request, queryset):
        """
        Export the selected objects to a CSV file.
        """
        model = queryset.model
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model._meta}.csv"'

        writer = csv.writer(response)
        # Write the header row
        writer.writerow([field.verbose_name for field in queryset.model._meta.fields])
        # Write the data rows
        for obj in queryset:
            row = []
            for field in queryset.model._meta.fields:
                if field.choices:
                    value = dict(field.choices).get(getattr(obj, field.name), None)
                    row.append(value)
                else:
                    row.append(getattr(obj, field.name))
            writer.writerow(row)
        return response
    export_to_csv.short_description = "Export to CSV"


class AuditModelAdmin(admin.ModelAdmin):

    def log_change(self, request, obj, message):
        # переопределяем, чтобы не создавать стандартный лог
        pass

    def save_model(self, request, obj, form, change):
        changes = {}
        if change and hasattr(obj, 'track_changes'):
            changes = obj.track_changes(exclude_fields=['updated_at', 'modified'])
            if changes:
                readable_changes = []
                for field, (old, new) in changes.items():
                    model_field = obj._meta.get_field(field)
                    verbose_name = obj._meta.get_field(field).verbose_name

                    if model_field.choices:
                        try:
                            old_display = dict(model_field.flatchoices).get(old)
                            new_display = dict(model_field.flatchoices).get(new)
                        except Exception:
                            old_display, new_display = old, new
                    else:
                        old_display, new_display = old, new

                    readable_changes.append(f"{verbose_name}: {old_display} -> {new_display};")
                change_message = "\n".join(readable_changes)
                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ContentType.objects.get_for_model(obj).pk,
                    object_id=obj.pk,
                    object_repr=force_str(obj),
                    action_flag=CHANGE,
                    change_message=change_message
                )
        super().save_model(request, obj, form, change)
        if change and changes:
            sync_waiting_for_order_object(obj, changed_fields=changes)
            emit_order_lifecycle_events(obj, actor=request.user, changed_fields=changes)
            emit_order_updated_notifications(
                obj,
                actor=request.user,
                changed_fields=changes,
            )


class OrderStatusFilter(SimpleListFilter):
    title = 'Статус'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return OrderStatus.choices

    def queryset(self, request, queryset):
        if self.value():
            status_fields = [
                'orders_printer__status',
                'orders_transport__status',
                'orders_pc__status',
                'orders_aho__status',
                'orders_account__status',
                'orders_vks__status',
            ]
            q_objects = Q()
            for field in status_fields:
                q_objects |= Q(**{field: self.value()})

            return queryset.filter(q_objects)
        return queryset


class SupportSpecialistFilter(admin.SimpleListFilter):
    title = 'Исполнитель'
    parameter_name = 'support_specialist'
    objects = SupportSpecialistManager()

    def lookups(self, request, model_admin):

        support_specialists = SupportSpecialist.objects.all()
        return [(user.id, user) for user in support_specialists]

    def queryset(self, request, queryset):
        support_specialist_id = self.value()

        if support_specialist_id:
            if queryset.model is Order:
                support_specialist_fields = [
                    'orders_printer__support_specialist_id',
                    'orders_transport__support_specialist_id',
                    'orders_pc__support_specialist_id',
                    'orders_aho__support_specialist_id',
                    'orders_account__support_specialist_id',
                    'orders_vks__support_specialist_id',
                ]
                q_objects = Q()
                for field in support_specialist_fields:
                    q_objects |= Q(**{field: support_specialist_id})
                return queryset.filter(q_objects)

            return queryset.filter(support_specialist_id=support_specialist_id)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # to have a date-based drilldown navigation in the admin page
    date_hierarchy = 'action_time'

    # to filter the resultes by telegram, content types and action flags
    list_filter = [
        'action_flag',

    ]

    # when searching the user will be able to search in both object_repr and change_message
    search_fields = [
        'object_repr',
        'change_message'
    ]
    list_display = [
        '__str__',
        'action_time',
        'user',
        'content_type',
        'action_flag',
        'object_link',
    ]
    fields = ('user', 'content_type', 'object_repr', 'action_flag', 'action_time', 'decoded_change_message')

    def decoded_change_message(self, obj):
        try:
            if isinstance(obj.change_message, str) and obj.change_message.startswith('['):
                data = json.loads(obj.change_message)
                changes = []
                for entry in data:
                    if 'changed' in entry:
                        fields = entry['changed'].get('fields', [])
                        changes.append('Изменены поля: ' + ', '.join(fields))
                    elif 'added' in entry:
                        changes.append(f"Добавлено: {entry['added'].get('name')}")
                    elif 'deleted' in entry:
                        changes.append(f"Удалено: {entry['deleted'].get('name')}")
                return format_html('<br>'.join(changes))
            return obj.change_message
        except Exception as e:
            logger.exception('admin log entry decode failed log_entry_id=%s', obj.pk)
            return f'Ошибка при декодировании: {e}'
    decoded_change_message.short_description = "Сообщение об изменениях"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = '<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return mark_safe(link)

    object_link.allow_tags = True
    object_link.admin_order_field = "object_repr"
    object_link.short_description = 'Объект'


@admin.register(Order)
class OrderAdmin(AuditModelAdmin):
    """
    Конфигурация администратора для модели Order.
    """
    actions = [
        'mail_to_admins',
    ]
    change_form_template = 'orders/admin/change_form.html'
    list_display_links = ('content_object',)
    list_display = [
        'id',
        'content_object',
        'owner',
        'created_at',
        '_support_specialist',
        'get_status',
    ]
    list_filter = ('created_at', OrderStatusFilter, SupportSpecialistFilter)

    def get_queryset(self, request):
        """
        Возвращает набор запросов для представления списка администратора с предварительной выборкой связанных объектов.
        """
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'owner',
            'content_type',
        ).prefetch_related(
            'content_object',
            'content_object__support_specialist__user',
        )

        return queryset

    def _support_specialist(self, obj):
        return obj.content_object.support_specialist
    _support_specialist.short_description = 'Исполнитель'

    def content_object(self, obj):
        """
        Возвращает ссылку на объект в админке.
        """
        content_object = obj.content_object
        if content_object is not None:
            content_type = obj.content_type
            url = reverse(f"admin:{content_type.app_label}_{content_type.model}_change", args=[content_object.pk])
            return format_html('<a href="{}">{}</a>', url, content_object)
        else:
            return '-'
    content_object.short_description = 'Категория'

    @admin.action(description='Отправить админам на почту')
    def mail_to_admins(self, request, queryset):
        """
        Sending mail notification to admins in settings.ADMINS
        """
        from apps.orders.tasks import task_mail_admins
        if not settings.DEBUG:
            for order in queryset:
                task_mail_admins.delay(order.id)
            self.message_user(request, 'Успешно отправлено админам на почту', messages.SUCCESS)
        else:
            self.message_user(request, 'В режиме DEBUG запрещено отправлять уведомления', level=messages.WARNING)


@admin.register(OrderPrinter)
class OrderPrinterAdmin(AuditModelAdmin):
    change_form_template = 'orders/admin/change_form.html'
    readonly_fields = ['created_at', ]
    actions = ['make_checked', 'make_done', 'make_unchecked', 'mail_organisation', 'export_to_csv']
    list_display = [
        'id',
        'client',
        'departament',
        'cabinet',
        'category',
        'created_at',
        'support_specialist',
        'status',
        'checked',
        'emailed_to_organisation',
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ('status', 'created_at',),
                    'support_specialist',
                )
            }
        ),
        (
            "Информация о заявителе",
            {
                "fields": (
                    'departament',
                    "owner",
                    (
                        "client",
                        "phone",),
                    (
                        "address",
                        'cabinet',
                    ),
                ),
            },
        ),
        (
            "Информация о заявке",
            {
                "fields": (
                    'category',
                    'printer_name',
                    "description",
                ),
            },
        ),
    )

    list_filter = [
        'created_at',
        ('created_at', filters.DateRangeFilter),
        'status',
        'category',
        SupportSpecialistFilter,
        'checked',
        'checked',
        'emailed_to_organisation',
        'client', ]
    search_fields = ['client', 'departament', ]

    def get_queryset(self, request):
        """
        Возвращает набор запросов для представления списка администратора с предварительной выборкой связанных объектов.
        """
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('owner',).prefetch_related('support_specialist__user')

        return queryset

    @admin.action(description='export_to_csv')
    def export_to_csv(self, request, queryset):
        # TODO make it for all models and moar output formats
        model = queryset.model
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model}.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Owner', 'Client', 'Printer Name', 'Printer Category', 'Status'])
        for order in queryset:
            writer.writerow([order.id, order.owner, order.client, order.printer_name,
                             order.get_category_display(), order.get_status_display()])
        return response

    export_to_csv.short_description = "Export to CSV"

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True

    @admin.action(description='Отправить в Техно-сервис')
    def mail_organisation(self, request, queryset):
        """
        Sending mail notification to organisation in settings.EMAIL_TECHNO_SERVICE
        """
        from apps.orders.tasks import task_mail_organisation_from_admin_panel
        if not settings.DEBUG:
            for order_printer in queryset:
                task_mail_organisation_from_admin_panel.delay(order_printer.id)
            queryset.update(status=OrderStatus.IN_WORK, emailed_to_organisation=True)
            self.message_user(request, f'Успешно отправлено {settings.EMAIL_TECHNO_SERVICE}', messages.SUCCESS)
        else:
            self.message_user(request, 'В режиме DEBUG запрещено отправлять уведомления', level=messages.WARNING)

    @admin.action(description='Выполнено')
    def make_done(self, request, queryset):
        queryset.update(status=OrderStatus.DONE)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)

    @admin.action(description='Проверено')
    def make_checked(self, request, queryset):
        queryset.update(checked=True)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)

    @admin.action(description='Не проверено')
    def make_unchecked(self, request, queryset):
        queryset.update(checked=False)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)


@admin.register(OrderTransport)
class OrderTransportAdmin(AuditModelAdmin, ExportCsvMixin):
    change_form_template = 'orders/admin/change_form.html'
    # action_form = UpdateActionForm
    readonly_fields = ['created_at', ]
    actions = [
        'make_done',
        'export_to_csv',
    ]  # 'export_as_json']
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ('status', 'created_at',),
                )
            }
        ),
        (
            "Информация о заявителе",
            {
                "fields": (
                    'departament',
                    "owner",
                    "client",
                    "phone",
                ),
            },
        ),
        (
            "Информация о заявке",
            {
                "fields": (
                    (
                        'transport_city',
                        'transport_passengers',
                    ),
                    'address',
                    (
                        'transport_arrival_datetime',
                        'comeback_datetime',
                    ),
                    'description',
                ),
            },
        ),
        (
            " ",
            {
                "fields": (
                    'driver',
                    'transport_departure_location',
                    'transport_departure_datetime',
                ),
            },
        ),
    )

    list_display = [
        'id',
        'client',
        'departament',
        'transport_city',
        'transport_arrival_datetime',
        'driver_link',
        'created_at',
        'status',
    ]
    list_display_links = ('id',)
    search_fields = ('client', 'departament', 'transport_arrival_datetime')
    list_filter = [
        'created_at',
        ('created_at', filters.DateRangeFilter),
        'status',
        'driver',
        'client',
    ]

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield: Field = super().formfield_for_dbfield(db_field, **kwargs)

        def make_field_wider(field):
            field.widget.attrs.update({'rows': 5, 'class': 'vLargeTextField'})
            field.widget = forms.Textarea(attrs=field.widget.attrs)

        if db_field.name == 'address':
            make_field_wider(formfield)
            formfield.label = 'Маршрут'
        if db_field.name == 'description':
            make_field_wider(formfield)
            formfield.label = 'Комментарий'

        return formfield

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('driver', 'owner', 'driver__car')
        return queryset

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser
        disabled_fields = set()
        if not is_superuser:
            disabled_fields |= {
                'owner',
            }
        for f in disabled_fields:
            if f in form.base_fields:
                form.base_fields[f].disabled = True
        return form

    def driver_link(self, obj):
        """
        Создаёт линк на водителя
        """
        if obj.driver is None:
            return

        url = reverse("admin:garage_driver_changelist") + urlencode(obj.driver.pk)
        return format_html('<a href="{}">{}</a>', url, obj.driver)

    driver_link.short_description = "Водитель"

    def order_transport_link(self, obj):
        """
        Создаёт линк на заявку на транспорт
        """

        if obj is None:
            return

        url = reverse("admin:orders_ordertransport_change", args=(obj.pk,))
        return format_html('<a href="{}">{}</a>', url, obj)

    # @admin.action(description='export')
    # def export_as_json(self, request, queryset):
    #     from django.core import serializers
    #     from django.http import HttpResponse
    #     response = HttpResponse(content_type="application/json")
    #     serializers.serialize("xml", queryset, stream=response)
    #     print(request.POST['price'])
    #     return response

    @admin.action(description='Выполнена')
    def make_done(self, request, queryset):
        queryset.update(status=OrderStatus.DONE)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)

    @admin.action(description='Отправить на почту пользователю')
    def send_email_to_user(self, request, queryset):
        logger.info(
            'admin transport email action invoked actor_id=%s selected_orders=%s',
            request.user.pk,
            queryset.count(),
            extra={'event': 'admin_transport_email_action'},
        )

    @admin.action(description='Отправить уведомление заявителю в телеграм')
    def send_telegram(self, request, queryset):
        users = [order.owner for order in queryset]
        for user in users:
            user.send_telegram_message('qq')
        self.message_user(
            request,
            f'Отправлено пользователям {[user for user in users]}',
            level=messages.SUCCESS
        )

    @admin.action(description='Отправить уведомление пользователю')
    def notification_user(self, request, queryset):
        from apps.orders.tasks import task_notification_user
        if not settings.DEBUG:
            for order in queryset:
                task_notification_user.delay(transport_id=order.id)
            self.message_user(
                request,
                f'Отправлено пользователю {request.user}',
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'В режиме DEBUG запрещено отправлять уведомления',
                level=messages.WARNING
            )


@admin.register(OrderPC)
class OrderPcAdmin(AuditModelAdmin, ExportCsvMixin):
    change_form_template = 'orders/admin/change_form.html'
    readonly_fields = ['created_at', ]
    actions = ['make_done', 'export_to_csv']
    list_display = [
        'id',
        'client',
        'departament',
        'category',
        'created_at',
        'support_specialist',
        'status',
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ('status', 'created_at',),
                    'support_specialist',
                )
            }
        ),
        (
            "Информация о заявителе",
            {
                "fields": (
                    'departament',
                    "owner",
                    (
                        "client",
                        "phone",),
                    (
                        "address",
                        'cabinet',
                    ),
                ),
            },
        ),
        (
            "Информация о заявке",
            {
                "fields": (
                    'category',
                    "description",
                ),
            },
        ),
    )
    search_fields = ('client', 'departament', 'description')
    list_filter = ['created_at', 'status', SupportSpecialistFilter, 'category', 'client']

    def get_queryset(self, request):

        queryset = super().get_queryset(request)
        queryset = queryset.select_related('owner',).prefetch_related('support_specialist__user')
        return queryset

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_data = {'custom_data': 'Custom data for this object'}
        if extra_context is None:
            extra_context = {}
        extra_context.update(extra_data)

        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True

    @admin.action(description='Выполнена')
    def make_done(self, request, queryset):
        queryset.update(status=OrderStatus.DONE)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)


@admin.register(OrderAho)
class OrderAhoAdmin(AuditModelAdmin, ExportCsvMixin):
    change_form_template = 'orders/admin/change_form.html'
    readonly_fields = ['created_at', ]
    actions = ['make_done', 'export_to_csv']
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ('status', 'created_at',),
                )
            }
        ),
        (
            "Информация о заявителе",
            {
                "fields": (
                    'departament',
                    "owner",
                    (
                        "client",
                        "phone",),
                    (
                        "address",
                        'cabinet',
                    ),
                ),
            },
        ),
        (
            "Информация о заявке",
            {
                "fields": (
                    'category',
                    "description",
                ),
            },
        ),
    )
    list_display = [
        'id',
        'client',
        'departament',
        'category',
        'created_at',
        'status',
    ]
    list_filter = ['created_at', 'status', 'category', 'client']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser
        disabled_fields = set()
        if not is_superuser:
            disabled_fields |= {
                'owner',
            }
        for f in disabled_fields:
            if f in form.base_fields:
                form.base_fields[f].disabled = True
        return form

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True

    @admin.action(description='Выполнена')
    def make_done(self, request, queryset):
        queryset.update(status=OrderStatus.DONE)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)


@admin.register(OrderAccount)
class OrderAccountAdmin(AuditModelAdmin, ExportCsvMixin):
    change_form_template = 'orders/admin/change_form.html'
    readonly_fields = ['created_at', ]
    actions = ['make_done', 'export_to_csv']
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ('status', 'created_at',),
                    'support_specialist',
                )
            }
        ),
        (
            "Информация о заявителе",
            {
                "fields": (
                    'departament',
                    'post',
                    "owner",
                    (
                        "client",
                        "phone",),
                    (
                        "address",
                        'cabinet',
                    ),
                ),
            },
        ),
        (
            "Информация о заявке",
            {
                "fields": (
                    'category',
                    "description",
                ),
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "pc_name",
                    "email_needed",
                    "tranzit_folder",
                    "sedo",
                    "information_systems",
                ),
            },
        ),
    )
    list_display = [
        'id',
        'client',
        'departament',
        'category',
        'created_at',
        'support_specialist',
        'status',
    ]
    list_filter = ['created_at', 'status', 'category', 'client']

    def get_queryset(self, request):
        """
        Возвращает набор запросов для представления списка администратора с предварительной выборкой связанных объектов.
        """
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('support_specialist', 'owner', )

        return queryset

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser
        disabled_fields = set()
        if not is_superuser:
            disabled_fields |= {
                'owner',
            }
        for f in disabled_fields:
            if f in form.base_fields:
                form.base_fields[f].disabled = True
        return form

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True

    @admin.action(description='Выполнена')
    def make_done(self, request, queryset):
        queryset.update(status=OrderStatus.DONE)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)


@admin.register(OrderVKS)
class OrderVKSAdmin(AuditModelAdmin, ExportCsvMixin):
    change_form_template = 'orders/admin/change_form.html'
    readonly_fields = ['created_at']
    actions = ['make_done', 'export_to_csv']
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ('status', 'created_at'),
                    'support_specialist',
                )
            }
        ),
        (
            "Информация о заявителе",
            {
                "fields": (
                    'departament',
                    'owner',
                    ('client', 'phone'),
                    ('address', 'cabinet'),
                ),
            },
        ),
        (
            "Информация о заявке",
            {
                "fields": (
                    'category',
                    'name_vks',
                    'recipient_email',
                    'link_vks',
                    'start_vks_datetime',
                    'duration_vks_time',
                    'equipment',
                    'description',
                ),
            },
        ),
    )
    list_display = [
        'id',
        'client',
        'departament',
        'category',
        'start_vks_datetime',
        'created_at',
        'support_specialist',
        'status',
    ]
    list_filter = ['created_at', 'status', 'category', 'client']
    search_fields = ['client', 'departament', 'name_vks', 'link_vks', 'recipient_email', 'description']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('owner').prefetch_related('support_specialist__user')
        return queryset

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True

    @admin.action(description='Выполнена')
    def make_done(self, request, queryset):
        queryset.update(status=OrderStatus.DONE)
        self.message_user(request, 'Успешно изменено', messages.SUCCESS)


@admin.register(Feedback)
class FeedbackAdmin(AuditModelAdmin, ExportCsvMixin):
    change_form_template = 'orders/admin/change_form.html'
    list_display = ['id', 'from_user', 'message', 'created_at']
    search_fields = ['from_user', 'message', ]
    actions = ['export_to_csv', ]

    def get_queryset(self, request):

        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('from_user', )
        return queryset

    def has_add_permission(self, request):
        return False if not request.user.is_superuser else True


@admin.register(OrderWorkflowRule)
class OrderWorkflowRuleAdmin(admin.ModelAdmin):
    list_display = ("category_label", "technical_group", "auto_assign_enabled", "assignment_strategy")
    list_filter = ("auto_assign_enabled", "assignment_strategy", "technical_group")
    search_fields = ("content_type__app_label", "content_type__model", "technical_group__name", "moderator_groups__name", "eligible_specialists__user__full_name", "eligible_specialists__user__username")
    filter_horizontal = ("moderator_groups", "eligible_specialists")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content_type", "technical_group")
