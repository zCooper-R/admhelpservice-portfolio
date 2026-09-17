from django.conf import settings
from django.db import models


class OrderMessageAttachment(models.Model):
    message = models.ForeignKey(
        "order_communication.OrderMessage",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="order_communication/%Y/%m/%d/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_order_message_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = "Order message attachment"
        verbose_name_plural = "Order message attachments"
        indexes = [
            models.Index(fields=["message", "created_at"], name="oc_att_message_created_idx"),
        ]

    def __str__(self):
        return self.original_name
