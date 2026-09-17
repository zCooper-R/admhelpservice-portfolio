from django.db import models


class MessageType(models.TextChoices):
    PUBLIC_REPLY = "public_reply", "Public reply"
    INTERNAL_NOTE = "internal_note", "Internal note"
    SYSTEM_EVENT = "system_event", "System event"


class MessageVisibility(models.TextChoices):
    REQUESTER_AND_STAFF = "requester_and_staff", "Requester and staff"
    STAFF_ONLY = "staff_only", "Staff only"


class SystemEventType(models.TextChoices):
    TICKET_CREATED = "ticket_created", "Ticket created"
    STATUS_CHANGED = "status_changed", "Status changed"
    ASSIGNMENT_CHANGED = "assignment_changed", "Assignment changed"
    PRIORITY_CHANGED = "priority_changed", "Priority changed"
    MESSAGE_DELETED = "message_deleted", "Message deleted"
