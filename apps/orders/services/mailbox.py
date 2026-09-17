import email
import imaplib
import logging
import re

from email.header import decode_header

from django.conf import settings

from apps.orders.choices import OrderStatus
from apps.orders.models.printer import OrderPrinter


logger = logging.getLogger('adm.integrations.mailbox')


class MailboxHandler:
    def __init__(self, imap_server, mail_login, mail_pass):
        self.imap_server = imap_server
        self.mail_login = mail_login
        self.mail_pass = mail_pass
        self.imap_connection = None
        self._current_folder = None

    def __enter__(self):
        self.connect()
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.imap_connection:
            self.imap_connection.logout()

    def connect(self):
        self.imap_connection = imaplib.IMAP4_SSL(self.imap_server)

    def login(self):
        self.imap_connection.login(self.mail_login, self.mail_pass)
        self.imap_connection.select('INBOX')
        self._current_folder = 'INBOX'

    @property
    def current_folder(self):
        return self._current_folder or 'INBOX'

    def switch_folder(self, folder_name):
        result, _ = self.imap_connection.select(folder_name)
        if result == 'OK':
            self._current_folder = folder_name
            logger.info('mailbox switched folder=%s', folder_name, extra={'event': 'mailbox_folder_switched'})
        else:
            logger.error('mailbox switch folder failed folder=%s', folder_name, extra={'event': 'mailbox_folder_switch_failed'})

    def fetch_unread_message_ids(self):
        status, response = self.imap_connection.search(None, 'UNSEEN')
        if status != 'OK':
            raise imaplib.IMAP4.error('Unable to fetch unread messages')
        return response[0].split()

    def fetch_message(self, msg_id):
        _, msg_data = self.imap_connection.fetch(msg_id, '(RFC822)')
        return msg_data[0][1]

    def extract_order_printer_id_from_email_message(self, message):
        pattern_subject = re.compile(r'№(\d+)')
        raw_email = message.decode('utf-8')
        parsed_email = email.message_from_string(raw_email)
        subject = decode_header(parsed_email['Subject'])[0][0].decode('utf-8')
        body = parsed_email.get_payload(0).as_string()

        if 'выполнено' in body.lower():
            matches_subject = pattern_subject.search(subject)
            if matches_subject:
                return matches_subject.group(1)
        return None


def process_done_order_printer_fill_emails():
    with MailboxHandler(settings.EMAIL_HOST, settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD) as imap_connection:
        imap_connection.switch_folder('TechnoService')
        try:
            unread_msg_ids = imap_connection.fetch_unread_message_ids()
            order_printer_ids = []
            for msg_id in unread_msg_ids:
                msg = imap_connection.fetch_message(msg_id)
                order_printer_id = imap_connection.extract_order_printer_id_from_email_message(msg)
                if order_printer_id:
                    order_printer_ids.append(order_printer_id)
            orders_updated = OrderPrinter.objects.filter(pk__in=order_printer_ids).update(status=OrderStatus.DONE)
            logger.info(
                'mailbox processed unread_messages=%s matched_orders=%s updated_orders=%s',
                len(unread_msg_ids),
                len(order_printer_ids),
                orders_updated,
                extra={'event': 'mailbox_processed'},
            )
        except imaplib.IMAP4.error:
            logger.exception('mailbox processing failed due_to=imap')
            raise
        except Exception:
            logger.exception('mailbox processing failed due_to=unexpected_error')
            raise
