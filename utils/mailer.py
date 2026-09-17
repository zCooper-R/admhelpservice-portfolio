import logging
import time

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.template.loader import get_template

from utils.logging_sanitizer import safe_recipient_count


logger = logging.getLogger('adm.integrations.mail')


class Mailer:
    """Send email messages helper class."""

    def __init__(self, from_email=None):
        if from_email is None:
            from_email = getattr(
                settings,
                'EMAIL_FROM',
                getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'webmaster@localhost')),
            )
        self.connection = mail.get_connection()
        self.from_email = from_email

    def __send_mail(self, mail_messages):
        started_at = time.monotonic()
        self.connection.open()
        try:
            sent_count = self.connection.send_messages(mail_messages)
            logger.info(
                'email batch sent messages=%s duration_ms=%s',
                sent_count or 0,
                int((time.monotonic() - started_at) * 1000),
                extra={'event': 'email_batch_sent'},
            )
        finally:
            self.connection.close()

    def __generate_messages(self, subject, template, context, to_emails):
        messages = []
        message_template = get_template(template)
        for recipient in to_emails:
            message_content = message_template.render(context)
            message = EmailMessage(subject, message_content, to=[recipient], from_email=self.from_email)
            message.content_subtype = 'html'
            messages.append(message)
        logger.info(
            'email batch prepared template=%s recipients=%s',
            template,
            safe_recipient_count(to_emails),
            extra={'event': 'email_batch_prepared'},
        )
        return messages

    def send_messages(self, subject, template, context, to_emails):
        messages = self.__generate_messages(subject, template, context, to_emails)
        self.__send_mail(messages)
