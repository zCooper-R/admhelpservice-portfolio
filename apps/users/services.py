import logging

from django.contrib.contenttypes.models import ContentType

from apps.orders.models.account import OrderAccount
from apps.orders.models.pc import OrderPC
from apps.orders.models.printer import OrderPrinter
from apps.orders.utils.telegram import build_notification_message
from utils.tlg_sender import TelegramSender


logger = logging.getLogger('adm.apps.users')


def send_order_object_telegram(object_id: int, content_type_model: str, tlg_ids: (list, tuple)):
    ct = ContentType.objects.get(model=content_type_model)
    obj = ct.get_object_for_this_type(id=object_id)
    message = build_notification_message(obj, ct)
    TelegramSender().send_messages(tlg_ids, message)
    logger.info(
        'order telegram sent content_type=%s object_id=%s recipients=%s',
        content_type_model,
        object_id,
        len(tlg_ids or []),
        extra={'event': 'order_object_telegram_sent'},
    )


def notify_specialist(object_id, content_type_model):
    try:
        ct = ContentType.objects.get(model=content_type_model)
        obj = ct.get_object_for_this_type(id=object_id)
        specialist = obj.support_specialist
        logger.info(
            'specialist notification requested content_type=%s object_id=%s',
            content_type_model,
            object_id,
            extra={'event': 'specialist_notification_requested'},
        )

        if not specialist or not specialist.have_tlg_id or not specialist.want_receive_telegram_notifications:
            logger.info(
                'specialist notification skipped content_type=%s object_id=%s has_specialist=%s has_tlg=%s notifications_enabled=%s',
                content_type_model,
                object_id,
                bool(specialist),
                bool(specialist and specialist.have_tlg_id),
                bool(specialist and specialist.want_receive_telegram_notifications),
                extra={'event': 'specialist_notification_skipped'},
            )
            return

        message = build_notification_message(obj, ct)
        specialist.send_telegram_message(message=message)
        logger.info(
            'specialist notified content_type=%s object_id=%s specialist_id=%s',
            content_type_model,
            object_id,
            specialist.pk,
            extra={'event': 'specialist_notified'},
        )

    except OrderPrinter.DoesNotExist:
        logger.warning('specialist notification skipped content_type=%s object_id=%s reason=printer_not_found', content_type_model, object_id)
    except OrderPC.DoesNotExist:
        logger.warning('specialist notification skipped content_type=%s object_id=%s reason=pc_not_found', content_type_model, object_id)
    except OrderAccount.DoesNotExist:
        logger.warning('specialist notification skipped content_type=%s object_id=%s reason=account_not_found', content_type_model, object_id)
