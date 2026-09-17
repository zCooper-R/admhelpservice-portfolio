import logging
import time

import telebot
from django.conf import settings

from utils.logging_sanitizer import safe_recipient_count


logger = logging.getLogger('adm.integrations.telegram')


class TelegramSender:
    def __init__(self, token=None):
        if token is None:
            token = settings.TELEGRAM_BOT_TOKEN
        self._token = token
        self.bot = telebot.TeleBot(self._token)

    def _send_message(self, tlg_id, message):
        started_at = time.monotonic()
        self.bot.send_message(chat_id=tlg_id, text=message)
        logger.info(
            'telegram message sent duration_ms=%s',
            int((time.monotonic() - started_at) * 1000),
            extra={'event': 'telegram_message_sent'},
        )

    def send_message(self, tlg_id, message):
        self._send_message(tlg_id, message)

    def send_messages(self, tlg_ids: (list, tuple), message):
        if not isinstance(tlg_ids, (list, tuple)):
            raise ValueError('tlg_ids must be list or tuple')

        logger.info(
            'telegram batch sending recipients=%s',
            safe_recipient_count(tlg_ids),
            extra={'event': 'telegram_batch_sending'},
        )
        for tlg_id in tlg_ids:
            self._send_message(tlg_id=tlg_id, message=message)
