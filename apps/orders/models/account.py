from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from apps.orders.choices import OrderAccountCategory
from apps.orders.models.base import BaseOrder


class OrderAccount(BaseOrder):
    """
    Модель заявки Учетная запись
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='ordersaccount',
        on_delete=models.SET_NULL,
        verbose_name='Создатель заявки',
        null=True
    )

    category = models.PositiveSmallIntegerField(
        choices=OrderAccountCategory.choices,
        verbose_name='Подкатегория'
    )
    post = models.CharField(verbose_name='Должность сотрудника', max_length=150, blank=True)
    pc_name = models.CharField(verbose_name='Имя компьютера', max_length=150,  blank=True)
    email_needed = models.BooleanField(verbose_name='Служебная электронная почта', default=False, blank=True)
    tranzit_folder = models.BooleanField(verbose_name='Доступ к папке "Документы отдела"', default=False, blank=True)
    sedo = models.BooleanField(verbose_name='Учётная запись СЭДО', default=False, blank=True)
    information_systems = models.BooleanField(verbose_name='Доступ к информационным системам(ИС)', default=False, blank=True)

    orders = GenericRelation('Order', related_query_name='orders_account')

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

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return 'orders/email/admin/orderaccount_email_to_admin.html'

    @property
    def is_sedo_category(self) -> bool:
        """
        True если заявка на аккаунт в категории СЭДО
        """
        return self.category == OrderAccountCategory.SEDO

    @property
    def is_information_systems_category(self) -> bool:
        """
        True если заявка на аккаут в категории Информационные системы
        """
        return self.category == OrderAccountCategory.INFORMATION_SYSTEMS

    def get_category_display_name(self):
        return f'Учётная запись-{self.get_category_display()}'
