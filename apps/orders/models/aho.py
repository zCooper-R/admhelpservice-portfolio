from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from apps.orders.choices import OrderAhoCategory
from apps.orders.models.base import BaseOrder


class OrderAho(BaseOrder):
    """
    Модель заявки Административно хозяйственного отдела
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='ordersaho',
        on_delete=models.SET_NULL,
        verbose_name='Создатель заявки',
        null=True
    )

    category = models.PositiveSmallIntegerField(
        choices=OrderAhoCategory.choices,
        verbose_name='Подкатегория'
    )

    orders = GenericRelation('Order', related_query_name='orders_aho')

    class Meta:
        verbose_name = 'Заявка в хоз. отдел'
        verbose_name_plural = 'Заявки хоз. отдела'
        ordering = ['-created_at']

    def __str__(self):
        return f'Хоз. отдел-{self.get_category_display()}'

    def get_absolute_url(self):
        return reverse('orders:order_aho_detail', kwargs={'pk': self.pk})

    def user_can_view_me(self, user):
        return user == self.owner or user.has_perm('orders.view_orderaho')

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
            'category': dict(OrderAhoCategory.choices)[self.category]
        }

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return 'orders/email/admin/orderaho_email_to_admin.html'

    def get_category_display_name(self):
        return f'Хоз. отдел-{self.get_category_display()}'
