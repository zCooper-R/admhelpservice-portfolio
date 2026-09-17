import logging

from celery import shared_task
from django.contrib.contenttypes.models import ContentType

from apps.users import telegram_messages
from apps.users.models import TechnicalGroup


logger = logging.getLogger(__name__)


@shared_task
def task_notify_telegram_technical_group_L1(object_id: int, content_type_model: str) -> None:
    highest_priority_group = TechnicalGroup.objects.order_by('priority').first()
    if highest_priority_group is None:
        logger.warning(
            'technical group notification skipped object_id=%s content_type=%s reason=no_groups',
            object_id,
            content_type_model,
            extra={'event': 'technical_group_notification_skipped'},
        )
        return

    specialists_in_group = highest_priority_group.specialists.filter(is_available=True)
    ct = ContentType.objects.get(model=content_type_model)
    obj = ct.get_object_for_this_type(pk=object_id)
    tlg_msg = telegram_messages.new_default_message
    if ct.model == 'orderprinter':
        tlg_msg = telegram_messages.new_printer_order_message
    if ct.model == 'orderpc':
        tlg_msg = telegram_messages.new_pc_order_message

    message = tlg_msg.format(
        category=obj.get_category_display(),
        id=obj.id,
        client=obj.client,
        address=obj.address,
        cabinet=obj.cabinet,
        phone=obj.phone,
    )
    delivered = 0
    for specialist in specialists_in_group:
        if specialist.have_tlg_id and specialist.want_receive_telegram_notifications:
            specialist.send_telegram_message(message=message)
            delivered += 1
    logger.info(
        'technical group notified content_type=%s object_id=%s recipients=%s',
        content_type_model,
        object_id,
        delivered,
        extra={'event': 'technical_group_notified'},
    )
