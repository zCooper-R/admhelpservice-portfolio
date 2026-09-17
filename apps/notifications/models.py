from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from apps.notifications.constants import NotificationEventType


class NotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(recipient=user)

    def unread(self):
        return self.filter(read_at__isnull=True)

    def read(self):
        return self.filter(read_at__isnull=False)


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_column="user_id",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
        null=True,
        blank=True,
    )
    event_type = models.CharField(
        max_length=64,
        choices=NotificationEventType.choices,
        default=NotificationEventType.ORDER_DETAILS_CHANGED,
    )
    title = models.CharField(max_length=254)
    body = models.TextField(db_column="message")
    created_at = models.DateTimeField(auto_now_add=True, db_column="timestamp", db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_targets",
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target_object = GenericForeignKey("target_content_type", "target_object_id")
    target_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient", "read_at", "created_at"], name="notif_recipient_read_idx"),
            models.Index(fields=["target_content_type", "target_object_id"], name="notif_target_idx"),
            models.Index(fields=["event_type", "created_at"], name="notif_event_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.recipient}: {self.title}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def get_target_url(self) -> str:
        if self.target_url:
            return self.target_url
        if self.target_object and hasattr(self.target_object, "get_absolute_url"):
            return self.target_object.get_absolute_url()
        return reverse("notifications:list")
