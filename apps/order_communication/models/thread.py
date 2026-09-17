from django.conf import settings
from django.db import models

from apps.orders.models.base import Order


class OrderThread(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="communication_thread",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_order_threads",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_public_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_internal_note_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_message_at", "-id"]
        verbose_name = "Order thread"
        verbose_name_plural = "Order threads"

    def __str__(self):
        return f"Thread for order #{self.order_id}"
