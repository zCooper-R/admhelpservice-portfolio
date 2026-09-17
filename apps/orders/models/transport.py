from datetime import datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from apps.garage.models import Driver
from apps.orders.models.base import BaseOrder


class OrderTransport(BaseOrder):
    """
    Модель заявки на служебный транспорт.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Создатель',
        related_name='orders_transport',
        on_delete=models.SET_NULL,
        null=True,
    )

    driver = models.ForeignKey(
        Driver,
        verbose_name='Водитель',
        related_name='orders_transport',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    transport_city = models.CharField(max_length=150, verbose_name='Город', default='Арзамас')
    transport_arrival_datetime = models.DateTimeField(verbose_name='Дата прибытия')
    transport_departure_datetime = models.DateTimeField(verbose_name='Дата отправления', blank=True, null=True)
    transport_departure_location = models.CharField(
        verbose_name='Место отправления',
        max_length=150,
        blank=True,
        null=True,
    )
    transport_passengers = models.PositiveSmallIntegerField(
        verbose_name='Количество сотрудников',
        default=1,
    )
    comeback = models.BooleanField(default=False)
    comeback_datetime = models.TimeField(verbose_name='Время возвращения', blank=True, null=True)

    orders = GenericRelation('Order', related_query_name='orders_transport')

    class Meta:
        verbose_name = 'Заявка на транспорт'
        verbose_name_plural = 'Заявки на транспорт'
        ordering = ['-created_at']

    def __str__(self):
        return f'Транспорт-{self.transport_city}'

    def get_absolute_url(self):
        return reverse('orders:order_transport_detail', kwargs={'pk': self.pk})

    def get_time_spent(self):
        if self.comeback:
            fmt = '%H:%M:%S'
            transport_arrival_datetime = datetime.strptime(str(self.transport_arrival_datetime.time()), fmt)
            comeback_datetime = datetime.strptime(str(self.comeback_datetime), fmt)
            return comeback_datetime - transport_arrival_datetime

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return 'orders/email/admin/ordertransport_email_to_admin.html'

    def get_category_display_name(self):
        return f'Транспорт-{self.transport_city}'
