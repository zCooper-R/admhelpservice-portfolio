from django.db import models
# from polymorphic.models import PolymorphicModel

from apps.users.models import User


class TimestampMixin(models.Model):
    """
    Абстрактная модель. Добавляет к модели
    дату создания и дату изменения.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')

    class Meta:
        abstract = True


class EthernetSocketConnection(TimestampMixin):
    pc_name = models.CharField(verbose_name='Имя устройства (кабинет)', max_length=155, unique=True)
    ethernet_socket = models.CharField(verbose_name='Номер розетки', max_length=155, unique=True)
    switch_num = models.PositiveSmallIntegerField(verbose_name='Номер коммутатора', default=0)
    switch_port = models.PositiveSmallIntegerField(verbose_name='Порт коммутатора', default=0)

    class Meta:
        verbose_name = 'Подключение интернет розеток'
        verbose_name_plural = 'Подключение интернет розеток'
        ordering = ['pc_name', 'ethernet_socket', ]

    def __str__(self):
        return f'{self.pc_name}:{self.ethernet_socket}'
