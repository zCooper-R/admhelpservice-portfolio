from django.db import models


class NotificationEventType(models.TextChoices):
    ORDER_CREATED = "order_created", "Создание заявки"
    ORDER_REQUIRES_REVIEW = "order_requires_review", "Заявка требует разбора"
    ORDER_STATUS_CHANGED = "order_status_changed", "Изменение статуса заявки"
    ORDER_COMPLETED = "order_completed", "Заявка выполнена"
    ORDER_REOPENED = "order_reopened", "Заявка возобновлена"
    ORDER_ASSIGNED = "order_assigned", "Назначение исполнителя"
    ORDER_UNASSIGNED = "order_unassigned", "Снятие исполнителя"
    ORDER_SENT_TO_SERVICE_ORGANIZATION = "order_sent_to_service_organization", "Заявка передана подрядчику"
    ORDER_COMMENT_ADDED = "order_comment_added", "Добавлен комментарий"
    ORDER_COMMENT_UPDATED = "order_comment_updated", "Обновлён комментарий"
    ORDER_REQUESTER_UPDATED = "order_requester_updated", "Заявитель обновил заявку"
    ORDER_DETAILS_CHANGED = "order_details_changed", "Изменены важные поля заявки"
    ORDER_SLA_REMINDER = "order_sla_reminder", "Напоминание о сроке ответа"
