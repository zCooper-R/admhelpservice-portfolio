from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from apps.orders.choices import OrderPrinterCategory
from apps.orders.models.base import BaseOrder


class OrderPrinter(BaseOrder):
    """
    Модель Заявки на обслуживание принтера.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Создатель',
        related_name='ordersprinter',
        on_delete=models.CASCADE,

    )
    printer_name = models.CharField(max_length=100, verbose_name='Имя принтера')

    category = models.PositiveSmallIntegerField(
        verbose_name='Подкатегория',
        choices=OrderPrinterCategory.choices,
    )

    checked = models.BooleanField(verbose_name='Проверено', default=False)

    orders = GenericRelation("Order", related_query_name='orders_printer')

    class Meta:
        verbose_name = 'Заявка на принтер'
        verbose_name_plural = 'Заявки на принтер'
        ordering = ['-created_at']

    def __str__(self):
        return f'Принтер-{self.get_category_display()}'

    def get_absolute_url(self):
        return reverse('orders:order_printer_detail', kwargs={'pk': self.pk})

    def user_can_view_me(self, user):
        return user == self.owner or user.has_perm('orders.view_orderprinter')

    def is_refill_category(self) -> bool:
        """
        True если заявка на принтер в категории заправка
        """
        return self.category == OrderPrinterCategory.REFILL

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        """
        Template path for notify admins by email
        """
        return 'orders/email/admin/orderprinter_email_to_admin.html'

    def get_category_display_name(self):
        return f'Принтер-{self.get_category_display()}'
