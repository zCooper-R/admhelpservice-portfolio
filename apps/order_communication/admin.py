from django.contrib import admin

from apps.order_communication.models import (
    OrderMessage,
    OrderMessageAttachment,
    OrderThread,
    OrderThreadReadState,
)


@admin.register(OrderThread)
class OrderThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "created_by", "last_message_at", "updated_at")
    list_select_related = ("order", "created_by")
    search_fields = ("order__id", "order__owner__username", "order__owner__full_name")
    readonly_fields = ("created_at", "updated_at", "last_message_at", "last_public_message_at", "last_internal_note_at")


@admin.register(OrderMessage)
class OrderMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "author", "message_type", "visibility", "created_at", "is_deleted")
    list_select_related = ("thread", "author", "edited_by", "deleted_by")
    list_filter = ("message_type", "visibility", "is_deleted", "created_at")
    search_fields = ("body", "thread__order__id", "author__username", "author__full_name")
    readonly_fields = ("created_at", "updated_at", "edited_at", "deleted_at")


@admin.register(OrderMessageAttachment)
class OrderMessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "original_name", "size", "uploaded_by", "created_at", "is_deleted")
    list_select_related = ("message", "uploaded_by")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("original_name", "message__thread__order__id")


@admin.register(OrderThreadReadState)
class OrderThreadReadStateAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "user", "last_read_message", "last_read_at", "updated_at")
    list_select_related = ("thread", "user", "last_read_message")
    search_fields = ("thread__order__id", "user__username", "user__full_name")
