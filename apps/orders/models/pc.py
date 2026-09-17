from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse

from apps.orders.choices import OrderPcCategory
from apps.orders.models.base import BaseOrder


class OrderPC(BaseOrder):
    """
    Модель заявки на Персональный Компьютер
    """

    owner = models.ForeignKey(
        "users.User",
        related_name="orderspc",
        on_delete=models.SET_NULL,
        verbose_name="Создатель заявки",
        null=True,
    )

    category = models.PositiveSmallIntegerField(
        choices=OrderPcCategory.choices,
        verbose_name="Подкатегория",
    )

    orders = GenericRelation("Order", related_query_name="orders_pc")

    class Meta:
        verbose_name = "Заявка на ПК"
        verbose_name_plural = "Заявки на ПК"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Компьютер-{self.get_category_display()}"

    def get_absolute_url(self):
        return reverse("orders:order_pc_detail", kwargs={"pk": self.pk})

    def user_can_view_me(self, user):
        return user == self.owner or user.has_perm("orders.view_orderpc")

    def get_context(self) -> dict:
        """
        Return context for templates
        """
        return {
            "owner": self.owner,
            "client": self.client,
            "address": self.address,
            "description": self.description,
            "phone": self.phone,
            "cabinet": self.cabinet,
            "category": dict(OrderPcCategory.choices)[self.category],
        }

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return "orders/email/admin/orderpc_email_to_admin.html"

    def get_category_display_name(self):
        return f"Компьютер-{self.get_category_display()}"
