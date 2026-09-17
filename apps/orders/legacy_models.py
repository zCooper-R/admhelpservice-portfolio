import datetime
import json
from abc import abstractmethod

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from django.db import models, transaction
from django.db.models import JSONField
from django.forms import model_to_dict

from django.urls import reverse
from django.utils.dateformat import DateFormat

from django.utils.html import format_html

from apps.garage.models import Driver
from apps.orders.choices import OrderStatus, OrderPrinterCategory, \
    OrderPcCategory, OrderAhoCategory, OrderVKSCategory, OrderDigitalSignCategory, OrderAccountCategory, \
    OrderSEDOCategory
from apps.orders.managers import OrderManager
from utils.tlg_sender import TelegramSender
from apps.users.models import SupportSpecialist, TechnicalGroup


class OrderSEDO(BaseOrder):
    """
    Модель заявки Учетная запись
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='orderssedo',
        on_delete=models.SET_NULL,
        verbose_name='Создатель заявки',
        null=True
    )

    category = models.PositiveSmallIntegerField(
        choices=OrderSEDOCategory.choices,
        verbose_name='Подкатегория'
    )
    post = models.CharField(verbose_name='Должность сотрудника', max_length=150, blank=True)
    pc_name = models.CharField(verbose_name='Имя компьютера', max_length=150,  blank=True)

    orders = GenericRelation('Order', related_query_name='orders_sedo')

    class Meta:
        verbose_name = 'Заявка на учётную запись'
        verbose_name_plural = 'Заявки на учётную запись'
        ordering = ['-created_at']

    def __str__(self):
        return f'Учётная запись-{self.get_category_display()}'

    def get_absolute_url(self):
        return reverse('orders:order_account_detail', kwargs={'pk': self.pk})

    def user_can_view_me(self, user):
        return user == self.owner or user.has_perm('orders.view_orderaccount')

    def get_context(self) -> dict:
        """
        Return context for templates
        """
        return {
            'owner': self.owner,
            'client': self.client,
            'address': self.address,
            'description': self.description,
            'phone': self.phone,
            'cabinet': self.cabinet,
            'category': dict(OrderAccountCategory.choices)[self.category]
        }

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return 'orders/email/admin/orderaccount_email_to_admin.html'

    def get_category_display_name(self):
        return f'Учётная запись-{self.get_category_display()}'


class OrderDigitalSign(BaseOrder):
    """
    Модель Заявки Цифровая подпись.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Создатель заявки',
        related_name='digitalsign',
        on_delete=models.CASCADE,

    )

    category = models.PositiveSmallIntegerField(
        verbose_name='Подкатегория',
        choices=OrderDigitalSignCategory.choices,
    )

    orders = GenericRelation("Order", related_query_name='orders_digitalsign')

    class Meta:
        verbose_name = 'Заявка на цифровую подпись'
        verbose_name_plural = 'Заявки на цифровую подпись'
        ordering = ['-created_at']

    def __str__(self):
        return f'ЭЦП-{self.get_category_display()}'

    # def get_absolute_url(self):
    #     return reverse('orders:order_printer_detail', kwargs={'pk': self.pk})

    def get_context(self) -> dict:
        """
        Context for templates
        """
        return {
            'owner': self.owner,
            'client': self.client,
            'address': self.address,
            'cabinet': self.cabinet,
            'phone': self.phone,
            'description': self.description,
            'category': dict(OrderDigitalSignCategory.choices)[self.category],

        }

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        """
        Template path for notify admins by email
        """
        return 'orders/email/admin/digital_sign_email_to_admin.html'

    def get_category_display_name(self):
        return f'ЭЦП-{self.get_category_display()}'


class Comment(TimeStampMixin):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               verbose_name='Автор',
                               on_delete=models.CASCADE,
                               related_name='comments'
                               )
    content = models.TextField(verbose_name='Содержание')

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return self.content


class Setting(TimeStampMixin):

    name = models.CharField(
        verbose_name="Имя переменной",
        max_length=200,
    )
    value = JSONField(null=True, blank=True,)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Настройка'
        verbose_name_plural = 'Настройки'
