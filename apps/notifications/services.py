from datetime import datetime
from typing import Dict, List, NamedTuple, Optional
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.notifications.constants import NotificationEventType
from apps.notifications.models import Notification
from apps.notifications.policies import (
    MODERATOR_AUDIENCE,
    REQUESTER_AUDIENCE,
    SPECIALIST_AUDIENCE,
    NotificationRoute,
    get_assignment_routes,
    get_change_routes,
    get_creation_routes,
)
from apps.orders.choices import OrderStatus


IMPORTANT_ORDER_FIELDS = {
    "address",
    "cabinet",
    "phone",
    "transport_arrival_datetime",
    "transport_departure_datetime",
    "transport_departure_location",
    "transport_passengers",
    "driver",
    "recipient_email",
    "link_vks",
    "start_vks_datetime",
    "duration_vks_time",
}


class NotificationPayload(NamedTuple):
    recipient: object
    title: str
    body: str
    event_type: str
    actor: Optional[object] = None
    target_object: Optional[object] = None
    target_url: str = ""
    metadata: Optional[Dict] = None


def _build_modal_target_url(order_object, audience: str) -> str:
    modal_url = order_object.get_absolute_url()
    base_url = reverse("orders:orders_list") if audience == REQUESTER_AUDIENCE else reverse("orders:tasks_list")
    query = urlencode({"modal": modal_url})
    return f"{base_url}?{query}"


def _order_ref(order_object) -> str:
    return f"заявка #{order_object.pk}"


def _order_ref_title(order_object) -> str:
    return f"Заявка #{order_object.pk}"


def _order_ref_genitive(order_object) -> str:
    return f"заявки #{order_object.pk}"


def _order_category_label(order_object) -> str:
    getter = getattr(order_object, "get_category_display_name", None)
    if callable(getter):
        return getter()
    return str(order_object._meta.verbose_name)


def _display_field_value(order_object, field_name: str, value) -> str:
    if value in (None, ""):
        return "не указано"

    field = order_object._meta.get_field(field_name)
    if field.choices:
        return dict(field.flatchoices).get(value, str(value))
    if hasattr(value, "user"):
        return str(value.user)
    if isinstance(value, datetime):
        local_dt = timezone.localtime(value) if timezone.is_aware(value) else value
        return local_dt.strftime("%d.%m.%Y %H:%M")
    return str(value)


def _get_important_field_names(changed_fields: dict) -> List[str]:
    return [field for field in changed_fields if field in IMPORTANT_ORDER_FIELDS]


def _get_important_field_labels(order_object, field_names: List[str]) -> List[str]:
    return [str(order_object._meta.get_field(field_name).verbose_name).strip() for field_name in field_names]


def _build_payload_for_route(
    *,
    route: NotificationRoute,
    actor,
    order_object,
    event_type: str,
    title: str,
    body: str,
    metadata: Optional[dict] = None,
) -> NotificationPayload:
    return NotificationPayload(
        recipient=route.recipient,
        actor=actor,
        target_object=order_object,
        target_url=_build_modal_target_url(order_object, route.audience),
        event_type=event_type,
        title=title,
        body=body,
        metadata=metadata,
    )


def create_notification(
    *,
    recipient,
    title: str,
    body: str,
    event_type: str,
    actor=None,
    target_object=None,
    target_url: str = "",
    metadata: Optional[dict] = None,
):
    if recipient is None:
        return None

    notification = Notification(
        recipient=recipient,
        actor=actor,
        event_type=event_type,
        title=title,
        body=body,
        target_url=target_url,
        metadata=metadata or {},
    )

    if target_object is not None:
        notification.target_content_type = ContentType.objects.get_for_model(target_object, for_concrete_model=False)
        notification.target_object_id = target_object.pk

    notification.save()
    return notification


def create_notifications(payloads: List[NotificationPayload]):
    notifications = []
    for payload in payloads:
        notifications.append(
            create_notification(
                recipient=payload.recipient,
                title=payload.title,
                body=payload.body,
                event_type=payload.event_type,
                actor=payload.actor,
                target_object=payload.target_object,
                target_url=payload.target_url,
                metadata=payload.metadata,
            )
        )
    return [item for item in notifications if item is not None]


def mark_notification_as_read(notification: Notification) -> Notification:
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return notification


def mark_all_notifications_as_read(user) -> int:
    return Notification.objects.for_user(user).unread().update(read_at=timezone.now())


def delete_all_notifications(user) -> int:
    deleted_count, _ = Notification.objects.for_user(user).delete()
    return deleted_count


def emit_order_created_notification(order_object, *, actor):
    payloads = []
    order_ref = _order_ref(order_object)
    category_label = _order_category_label(order_object)

    for route in get_creation_routes(order_object, actor=actor):
        if route.audience == MODERATOR_AUDIENCE:
            payloads.append(
                _build_payload_for_route(
                    route=route,
                    actor=actor,
                    order_object=order_object,
                    event_type=NotificationEventType.ORDER_REQUIRES_REVIEW,
                    title=f"Новая {order_ref} требует обработки",
                    body=f"Поступила {category_label.lower()}. Проверьте заявку и при необходимости скорректируйте исполнителя.",
                    metadata={"category": category_label},
                )
            )
            continue

        payloads.append(
            _build_payload_for_route(
                route=route,
                actor=actor,
                order_object=order_object,
                event_type=NotificationEventType.ORDER_ASSIGNED,
                title=f"Вам назначена {_order_ref(order_object)}",
                body=f"Новая {category_label.lower()} поступила в работу.",
                metadata={"category": category_label},
            )
        )

    if payloads:
        transaction.on_commit(lambda: create_notifications(payloads))


def _build_status_change_payloads(order_object, *, actor, old_status, new_status, important_field_labels: Optional[List[str]] = None):
    old_label = _display_field_value(order_object, "status", old_status)
    new_label = _display_field_value(order_object, "status", new_status)
    order_ref = _order_ref(order_object)
    order_ref_title = _order_ref_title(order_object)
    order_ref_genitive = _order_ref_genitive(order_object)
    metadata = {"old_status": old_status, "new_status": new_status}
    details_suffix = f" Также обновлены: {', '.join(important_field_labels)}." if important_field_labels else ""

    if new_status == OrderStatus.DONE:
        event_type = NotificationEventType.ORDER_COMPLETED
        requester_title = f"Ваша {order_ref} выполнена"
        requester_body = f"Работа по вашей {order_ref_genitive} завершена. Текущий статус: «{new_label}».{details_suffix}"
        internal_title = f"{order_ref_title} выполнена"
        internal_body = f"Статус {order_ref} изменён на «{new_label}»."
    elif old_status in {OrderStatus.DONE, OrderStatus.CLOSED, OrderStatus.CANCELED} and new_status in {OrderStatus.ACCEPTED, OrderStatus.IN_WORK}:
        event_type = NotificationEventType.ORDER_REOPENED
        requester_title = f"Ваша {order_ref} снова в работе"
        requester_body = f"Работа по вашей {order_ref_genitive} возобновлена. Текущий статус: «{new_label}».{details_suffix}"
        internal_title = f"{order_ref_title} возвращена в работу"
        internal_body = f"{order_ref_title} переведена в статус «{new_label}»."
    else:
        event_type = NotificationEventType.ORDER_STATUS_CHANGED
        requester_title = f"Статус вашей {order_ref_genitive} изменён"
        requester_body = f"Новый статус вашей {order_ref_genitive}: «{new_label}».{details_suffix}"
        internal_title = f"Изменён статус {order_ref}"
        internal_body = f"Статус {order_ref} изменён с «{old_label}» на «{new_label}»."

    payloads = []
    for route in get_change_routes(order_object, actor=actor):
        if route.audience == REQUESTER_AUDIENCE:
            title = requester_title
            body = requester_body
        elif route.audience == MODERATOR_AUDIENCE and actor == getattr(order_object, "owner", None):
            title = f"Заявитель обновил статус {order_ref}"
            body = f"По {order_ref} новый статус: «{new_label}»."
        else:
            title = internal_title
            body = internal_body

        payloads.append(
            _build_payload_for_route(
                route=route,
                actor=actor,
                order_object=order_object,
                event_type=event_type,
                title=title,
                body=body,
                metadata=metadata,
            )
        )
    return payloads


def _build_assignment_payloads(order_object, *, actor, old_specialist, new_specialist):
    payloads = []
    routes = get_assignment_routes(
        order_object,
        actor=actor,
        old_specialist=old_specialist,
        new_specialist=new_specialist,
    )
    order_ref = _order_ref(order_object)
    order_ref_title = _order_ref_title(order_object)
    previous_user = getattr(old_specialist, "user", None) if old_specialist else None
    current_user = getattr(new_specialist, "user", None) if new_specialist else None

    if routes.current_specialist:
        payloads.append(
            _build_payload_for_route(
                route=routes.current_specialist,
                actor=actor,
                order_object=order_object,
                event_type=NotificationEventType.ORDER_ASSIGNED,
                title=f"Вам назначена {order_ref}",
                body=f"{order_ref_title} закреплена за вами.",
                metadata={"specialist_id": getattr(current_user, "pk", None)},
            )
        )

    if routes.previous_specialist:
        payloads.append(
            _build_payload_for_route(
                route=routes.previous_specialist,
                actor=actor,
                order_object=order_object,
                event_type=NotificationEventType.ORDER_UNASSIGNED,
                title=f"{order_ref_title} передана другому исполнителю",
                body=f"Вы больше не назначены исполнителем по {order_ref}.",
                metadata={"specialist_id": getattr(previous_user, "pk", None)},
            )
        )

    if routes.requester:
        if current_user:
            title = f"Назначен исполнитель по {order_ref}"
            body = f"Исполнителем по вашей { _order_ref_genitive(order_object) } назначен {current_user}."
            event_type = NotificationEventType.ORDER_ASSIGNED
        else:
            title = f"Исполнитель по {order_ref} снят"
            body = f"По вашей {_order_ref_genitive(order_object)} сейчас нет назначенного исполнителя."
            event_type = NotificationEventType.ORDER_UNASSIGNED
        payloads.append(
            _build_payload_for_route(
                route=routes.requester,
                actor=actor,
                order_object=order_object,
                event_type=event_type,
                title=title,
                body=body,
                metadata={"specialist_id": getattr(current_user, "pk", None)},
            )
        )
    return payloads


def _build_comment_payloads(order_object, *, actor, old_comment, new_comment):
    event_type = NotificationEventType.ORDER_COMMENT_ADDED if not old_comment and new_comment else NotificationEventType.ORDER_COMMENT_UPDATED
    order_ref = _order_ref(order_object)
    order_ref_genitive = _order_ref_genitive(order_object)
    payloads = []

    for route in get_change_routes(order_object, actor=actor):
        if route.audience == REQUESTER_AUDIENCE:
            title = f"Комментарий по вашей {order_ref_genitive} обновлён"
            body = (
                f"По вашей {order_ref_genitive} появился новый комментарий."
                if event_type == NotificationEventType.ORDER_COMMENT_ADDED
                else f"Комментарий по вашей {order_ref_genitive} был обновлён."
            )
        elif route.audience == MODERATOR_AUDIENCE and actor == getattr(order_object, "owner", None):
            title = f"Заявитель обновил комментарий в {order_ref}"
            body = f"Проверьте новые детали по {order_ref}."
        elif route.audience == SPECIALIST_AUDIENCE and actor == getattr(order_object, "owner", None):
            title = f"Заявитель обновил {order_ref}"
            body = f"В {order_ref} появился новый комментарий от заявителя."
        else:
            title = f"Обновлён комментарий в {order_ref}"
            body = (
                f"В {order_ref} появился новый комментарий."
                if event_type == NotificationEventType.ORDER_COMMENT_ADDED
                else f"Комментарий в {order_ref} был обновлён."
            )

        payloads.append(
            _build_payload_for_route(
                route=route,
                actor=actor,
                order_object=order_object,
                event_type=event_type,
                title=title,
                body=body,
            )
        )
    return payloads


def _build_important_fields_payloads(order_object, *, actor, changed_fields, skip_requester: bool = False):
    important_fields = _get_important_field_names(changed_fields)
    if not important_fields:
        return []

    order_ref = _order_ref(order_object)
    order_ref_genitive = _order_ref_genitive(order_object)
    field_labels = _get_important_field_labels(order_object, important_fields)
    labels = ", ".join(field_labels)
    payloads = []
    actor_is_owner = actor == getattr(order_object, "owner", None)

    for route in get_change_routes(order_object, actor=actor):
        if skip_requester and route.audience == REQUESTER_AUDIENCE:
            continue

        event_type = NotificationEventType.ORDER_DETAILS_CHANGED
        if route.audience == REQUESTER_AUDIENCE:
            title = f"Детали вашей {order_ref_genitive} обновлены"
            body = f"По вашей {order_ref_genitive} обновлены важные детали."
        elif actor_is_owner and route.audience in {SPECIALIST_AUDIENCE, MODERATOR_AUDIENCE}:
            event_type = NotificationEventType.ORDER_REQUESTER_UPDATED
            title = f"Заявитель обновил {order_ref}"
            body = f"По {order_ref} обновлены поля: {labels}."
        else:
            title = f"Обновлены детали {order_ref}"
            body = f"По {order_ref} обновлены поля: {labels}."

        payloads.append(
            _build_payload_for_route(
                route=route,
                actor=actor,
                order_object=order_object,
                event_type=event_type,
                title=title,
                body=body,
                metadata={"fields": important_fields},
            )
        )
    return payloads


def emit_order_updated_notifications(order_object, *, actor, changed_fields: dict):
    if not changed_fields:
        return

    payloads = []
    important_field_names = _get_important_field_names(changed_fields)
    important_field_labels = _get_important_field_labels(order_object, important_field_names)
    skip_requester_details = "status" in changed_fields and bool(important_field_names)

    if "status" in changed_fields:
        old_status, new_status = changed_fields["status"]
        payloads.extend(
            _build_status_change_payloads(
                order_object,
                actor=actor,
                old_status=old_status,
                new_status=new_status,
                important_field_labels=important_field_labels,
            )
        )

    if "support_specialist" in changed_fields:
        old_specialist, new_specialist = changed_fields["support_specialist"]
        payloads.extend(
            _build_assignment_payloads(
                order_object,
                actor=actor,
                old_specialist=old_specialist,
                new_specialist=new_specialist,
            )
        )

    if "description" in changed_fields:
        old_comment, new_comment = changed_fields["description"]
        normalized_old_comment = (old_comment or "").strip() if isinstance(old_comment, str) else old_comment
        normalized_new_comment = (new_comment or "").strip() if isinstance(new_comment, str) else new_comment
        if normalized_old_comment != normalized_new_comment and normalized_new_comment:
            payloads.extend(
                _build_comment_payloads(
                    order_object,
                    actor=actor,
                    old_comment=normalized_old_comment,
                    new_comment=normalized_new_comment,
                )
            )

    payloads.extend(
        _build_important_fields_payloads(
            order_object,
            actor=actor,
            changed_fields=changed_fields,
            skip_requester=skip_requester_details,
        )
    )

    if payloads:
        transaction.on_commit(lambda: create_notifications(payloads))
