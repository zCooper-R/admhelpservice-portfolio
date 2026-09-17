from apps.orders.models.base import Order
from django.template.loader import render_to_string

from apps.orders.services.moderator_group_fetcher import ModeratorFromGroups
from utils.mailer import Mailer
from utils.tlg_sender import TelegramSender

import logging

logger = logging.getLogger(__name__)


class OrderNotifier:
    def __init__(self, order_id: int):
        self.order = Order.objects.select_related('content_type').get(id=order_id)
        self.obj = self.order.content_object
        self.category = self.obj.get_category_display_name()
        self.model_name = self.order.content_type.model

    def get_mail_subject(self):
        return f'Новая заявка {self.category} №{self.order.id}'

    def get_mail_template(self, to_group: str = 'admin'):
        return f'orders/email/{to_group}/{self.model_name}_email_to_{to_group}.html'

    def notify_admins_email(self):
        subject = self.get_mail_subject()
        html = render_to_string(self.get_mail_template(), {'object': self.obj})
        Mailer().send_admins(subject=subject, html_message=html)
        logger.info(f"[EMAIL] Админы уведомлены о {self.category} #{self.order.id}")

    def notify_moderators_tg(self):
        tg_ids = ModeratorFromGroups.get_tg_ids(self.model_name)
        if not tg_ids:
            logger.warning(f"[TG] Нет модераторов для модели {self.model_name}")
            return

        message = self.format_tg_message()
        TelegramSender().send_messages(tlg_ids=tg_ids, message=message)
        logger.info(f"[TG] Модераторы {self.model_name} уведомлены")

    def format_tg_message(self):
        lines = [
            '⚠️Новая заявка!⚠️',
            f'{self.category} #{self.order.id}',
        ]
        if hasattr(self.obj, 'client'):
            lines.append(f'👨 - {self.obj.client}')
        if hasattr(self.obj, 'address'):
            lines.append(f'🏢 - {self.obj.address}, каб.{getattr(self.obj, "cabinet", "")}')
        if hasattr(self.obj, 'phone'):
            lines.append(f'☎️ - {self.obj.phone}')
        return '\n'.join(lines)
