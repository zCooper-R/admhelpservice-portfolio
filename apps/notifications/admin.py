from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "actor", "event_type", "title", "read_at")
    list_select_related = ("recipient", "actor", "target_content_type")
    list_filter = ("event_type", "read_at", "created_at")
    search_fields = (
        "title",
        "body",
        "recipient__username",
        "recipient__full_name",
        "actor__username",
        "actor__full_name",
    )
    readonly_fields = ("created_at", "read_at", "target_content_type", "target_object_id", "metadata")
    ordering = ("-created_at", "-id")
