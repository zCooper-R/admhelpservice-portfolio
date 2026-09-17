import json
from abc import abstractmethod

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from apps.orders.choices import OrderStatus, OrderWaitingFor
from apps.orders.managers import OrderManager
from apps.orders.models.mixins import TimeStampMixin, ChoicesDisplayMixin, TrackChangesModel, OrderWrapperMixin


class BaseOrder(TrackChangesModel, OrderWrapperMixin, ChoicesDisplayMixin, TimeStampMixin):
    """
    Абстрактная модель Заявки.
    """

    client = models.CharField(max_length=100, verbose_name='Инициатор')
    title = models.CharField(max_length=100, verbose_name='Заголовок', blank=True)
    description = models.TextField(max_length=1000, verbose_name='Комментарий', blank=True)
    status = models.SmallIntegerField(choices=OrderStatus.choices, default=OrderStatus.ACCEPTED, verbose_name='Статус')
    address = models.CharField(max_length=450, verbose_name='Адрес')
    departament = models.CharField(max_length=250, verbose_name='Подразделение')
    cabinet = models.CharField(max_length=30, verbose_name='Кабинет')
    phone = models.CharField(max_length=50, verbose_name='Телефон')
    # answer = models.TextField(max_length=200, verbose_name='Ответ специалиста', blank=True)
    glpi = models.SmallIntegerField(verbose_name='GLPI_ID', blank=True, null=True)
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено')
    emailed_to_admin = models.BooleanField(default=False, verbose_name='Email админам')
    emailed_to_organisation = models.BooleanField(default=False, verbose_name='Email в организацию')
    emailed_to_user = models.BooleanField(default=False, verbose_name='Email юзеру')
    support_specialist = models.ForeignKey(
        'users.SupportSpecialist',
        verbose_name='Исполнитель',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,

    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'OrderID:{self.id}'

    @abstractmethod
    def get_template_mail_admin(self):
        pass

    @abstractmethod
    def get_category_display_name(self):
        pass


class Order(TimeStampMixin):
    objects = OrderManager()

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Создатель',
        related_name='orders',
        on_delete=models.SET_NULL,
        null=True

    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Изменено',
        related_name='updated_orders',
        on_delete=models.SET_NULL,
        null=True
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.RESTRICT,
        verbose_name='Тип объекта',
        related_name='%(class)s_content_object'
    )
    object_id = models.PositiveSmallIntegerField(verbose_name='ID объекта')
    content_object = GenericForeignKey("content_type", 'object_id')
    waiting_for = models.CharField(max_length=16, choices=OrderWaitingFor.choices, default=OrderWaitingFor.NONE, verbose_name='Ожидание ответа')
    waiting_since = models.DateTimeField(null=True, blank=True, verbose_name='Ожидает с')

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Все заявки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at'], name='orders_order_created_at_idx'),
            models.Index(fields=['owner', 'created_at'], name='orders_order_owner_created_idx'),
            models.Index(fields=['content_type', 'object_id'], name='orders_order_ct_object_idx'),
        ]

    def __str__(self):
        # return f'{self.content_type.model_class().__name__} #{self.object_id}'
        return f'{self.content_object}'

    def get_absolute_url(self):
        co = self.content_object
        if co is not None and hasattr(co, 'get_absolute_url'):
            return co.get_absolute_url()
        return reverse('orders:orders_list')

    def to_dict_json(self):
        return {
            'content_type': self.content_type,
            'object_id': self.object_id,
            'content_object': self.content_object,

        }

    def to_json(self):
        return json.dumps(self.to_dict_json())

    def get_client(self):
        return getattr(self.content_object, 'client', '—')
    get_client.short_description = 'Инициатор'

    def get_status(self):
        # если есть метод get_status_display у связанного объекта
        if hasattr(self.content_object, 'get_status_display'):
            return self.content_object.get_status_display()
        return '—'
    get_status.short_description = 'Статус'

    def get_support_specialist(self):
        return getattr(self.content_object, 'support_specialist', '—')
    get_support_specialist.short_description = 'Исполнитель'
