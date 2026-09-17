from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from apps.orders.choices import OrderVKSCategory, OrderVKSEquipment
from apps.orders.models.base import BaseOrder


class OrderVKS(BaseOrder):
    """
    Модель заявки ВКС.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='ordersvks',
        on_delete=models.SET_NULL,
        verbose_name='Создатель заявки',
        null=True
    )

    category = models.PositiveSmallIntegerField(
        choices=OrderVKSCategory.choices,
        verbose_name='Подкатегория'
    )

    equipment = models.CharField(
        max_length=255,
        verbose_name='Необходимое оборудование',
        blank=True
    )

    recipient_email = models.EmailField(
        verbose_name='Куда отправить ссылку',
        blank=True,
    )

    name_vks = models.CharField(
        max_length=255,
        verbose_name='Название трансляции',
        blank=True,
    )
    link_vks = models.CharField(
        max_length=255,
        verbose_name='Ссылка для подключения',
        blank=True,
    )
    start_vks_datetime = models.DateTimeField(
        verbose_name='Дата и время',
        blank=True,
        null=True
    )
    duration_vks_time = models.FloatField(
        verbose_name='Длительность (часы)',
        blank=True,
        null=True
    )

    orders = GenericRelation('Order', related_query_name='orders_vks')

    class Meta:
        verbose_name = 'Заявка ВКС'
        verbose_name_plural = 'Заявки ВКС'
        ordering = ['-created_at']

    def __str__(self):
        return f'ВКС-{self.get_category_display()}'

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return 'orders/email/admin/vks_email_to_admin.html'

    def get_absolute_url(self):
        return reverse('orders:order_vks_detail', kwargs={'pk': self.pk})

    def user_can_view_me(self, user):
        return user == self.owner or user.has_perm('orders.view_ordervks')

    def get_category_display_name(self):
        return f'ВКС-{self.get_category_display()}'

    def get_equipment_display_list(self):
        if not self.equipment:
            return []

        labels = []
        for raw_value in str(self.equipment).split(','):
            raw_value = raw_value.strip()
            if not raw_value:
                continue
            try:
                labels.append(OrderVKSEquipment(int(raw_value)).label)
            except ValueError:
                labels.append(raw_value)
        return labels

    def get_duration_display(self):
        if self.duration_vks_time in (None, ''):
            return ''

        value = float(self.duration_vks_time)
        if value.is_integer():
            return f'{int(value)} ч.'
        return f'{value:g} ч.'
