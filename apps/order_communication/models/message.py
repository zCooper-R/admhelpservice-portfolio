from django.conf import settings
from django.db import models

from apps.order_communication.constants import MessageType, MessageVisibility, SystemEventType


class OrderMessage(models.Model):
    thread = models.ForeignKey(
        "order_communication.OrderThread",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_messages",
    )
    message_type = models.CharField(max_length=32, choices=MessageType.choices, db_index=True)
    visibility = models.CharField(max_length=32, choices=MessageVisibility.choices, db_index=True)
    system_event_type = models.CharField(max_length=64, choices=SystemEventType.choices, blank=True)
    body = models.TextField(blank=True)
    body_rendered = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True, db_index=True)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_order_messages",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_order_messages",
    )

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "Order message"
        verbose_name_plural = "Order messages"
        indexes = [
            models.Index(fields=["thread", "created_at"], name="oc_msg_thr_created_idx"),
            models.Index(fields=["thread", "visibility", "created_at"], name="oc_msg_thr_vis_cr_idx"),
            models.Index(fields=["thread", "message_type", "created_at"], name="oc_msg_thr_type_cr_idx"),
            models.Index(fields=["thread", "is_deleted", "created_at"], name="oc_msg_thr_del_cr_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(message_type=MessageType.SYSTEM_EVENT, system_event_type__gt="")
                    | ~models.Q(message_type=MessageType.SYSTEM_EVENT)
                ),
                name="oc_msg_system_event_type_required",
            ),
        ]

    def __str__(self):
        return f"Message #{self.pk} for thread #{self.thread_id}"
