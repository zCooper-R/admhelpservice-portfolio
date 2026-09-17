from django.conf import settings
from django.db import models


class OrderThreadReadState(models.Model):
    thread = models.ForeignKey(
        "order_communication.OrderThread",
        on_delete=models.CASCADE,
        related_name="read_states",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="order_thread_read_states",
    )
    last_read_message = models.ForeignKey(
        "order_communication.OrderMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    unread_count_hint = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order thread read state"
        verbose_name_plural = "Order thread read states"
        constraints = [
            models.UniqueConstraint(fields=["thread", "user"], name="oc_read_thread_user_unique"),
        ]
        indexes = [
            models.Index(fields=["user", "last_read_at"], name="oc_read_user_last_read_idx"),
            models.Index(fields=["thread", "user"], name="oc_read_thread_user_idx"),
        ]

    def __str__(self):
        return f"Read state for thread #{self.thread_id} and user #{self.user_id}"
