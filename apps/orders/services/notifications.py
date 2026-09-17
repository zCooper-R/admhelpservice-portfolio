import logging

from django.conf import settings
from django.core import mail
from django.shortcuts import get_object_or_404
from django.template import loader

from apps.orders.models.account import OrderAccount
from apps.orders.models.aho import OrderAho
from apps.orders.models.base import Order
from apps.orders.models.feedback import Feedback
from apps.orders.models.pc import OrderPC
from apps.orders.models.printer import OrderPrinter
from apps.orders.models.transport import OrderTransport
from apps.users import services as user_services
from utils.mailer import Mailer
from utils.tlg_sender import TelegramSender


logger = logging.getLogger('adm.apps.orders.notifications')


class OrderNotificationService:
    @staticmethod
    def mail_admins_for_order(order_id: int, subject: str = None, context: dict = None, template: str = None) -> None:
        order = Order.objects.get(id=order_id)
        order_obj = order.content_type.get_object_for_this_type(pk=order.object_id)

        if subject is None:
            subject = f'Новая заявка #{order.id}'
        if context is None:
            context = {'object': order_obj}
        if template is None:
            template = order_obj.get_template_mail_admin()

        tmpl = loader.get_template(template)
        mail.mail_admins(subject=subject, message='', html_message=tmpl.render(context))
        logger.info('admins emailed order_id=%s template=%s', order_id, template, extra={'event': 'admins_emailed'})

    @staticmethod
    def mail_admins_feedback(feedback_id: int) -> None:
        feedback = Feedback.objects.get(id=feedback_id)
        user_email = ''
        if feedback.from_user:
            user_email = feedback.from_user.get_email() if hasattr(feedback.from_user, 'get_email') else feedback.from_user.email

        reply_email = feedback.email or user_email
        reply_email_line = f'E-mail для ответа: {reply_email}' if reply_email else 'Пользователь не указал email для ответа.'
        mail.mail_admins(
            subject=f'Обратная связь №{feedback.id}',
            message=f'От: {feedback.from_user}\n{reply_email_line}\nОбращение: {feedback.message}',
        )
        logger.info('feedback emailed feedback_id=%s has_reply_email=%s', feedback_id, bool(reply_email), extra={'event': 'feedback_emailed'})

    @staticmethod
    def mail_organisation_printer(order_printer_id: int, subject: str = None, context: dict = None, template: str = None) -> None:
        mailer = Mailer()
        ticket = OrderPrinter.objects.get(pk=order_printer_id)

        if context is None:
            context = {'object': ticket}
        if template is None:
            template = 'orders/email/organisation/orderprinter_email_to_organisation.html'
        if subject is None:
            subject = f'Заявка на обслуживание принтера №{ticket.id}'

        mailer.send_messages(subject=subject, template=template, context=context, to_emails=settings.EMAIL_TECHNO_SERVICE)
        ticket.emailed_to_organisation = True
        ticket.save(update_fields=['emailed_to_organisation', 'updated_at'])
        logger.info('organisation emailed printer_order_id=%s recipients=%s', order_printer_id, len(settings.EMAIL_TECHNO_SERVICE), extra={'event': 'organisation_emailed'})

    @staticmethod
    def mail_organisation_from_admin_panel(order_printer_id: int, subject: str = None, context: dict = None, template: str = None) -> None:
        mailer = Mailer()
        order_printer = OrderPrinter.objects.get(pk=order_printer_id)
        if context is None:
            context = {'object': order_printer}
        if template is None:
            template = 'orders/email/organisation/orderprinter_email_to_organisation.html'
        if subject is None:
            subject = f'Заявка на обслуживание принтера №{order_printer.id}'

        mailer.send_messages(subject=subject, template=template, context=context, to_emails=settings.EMAIL_TECHNO_SERVICE)
        order_printer.emailed_to_organisation = True
        order_printer.save(update_fields=['emailed_to_organisation', 'updated_at'])
        logger.info('organisation emailed from admin printer_order_id=%s', order_printer_id, extra={'event': 'organisation_emailed_admin'})

    @staticmethod
    def mail_protection_sector(order_account_id: int, subject: str = None, context: dict = None, template: str = None) -> None:
        mailer = Mailer()
        ticket = OrderAccount.objects.get(pk=order_account_id)

        if context is None:
            context = {'object': ticket}
        if template is None:
            template = ticket.get_template_mail_admin()
        if subject is None:
            subject = f'Заявка учетная запись №{ticket.id}'

        mailer.send_messages(
            subject=subject,
            template=template,
            context=context,
            to_emails=settings.PROTECTION_SECTOR_EMAILS,
        )
        logger.info('protection sector emailed order_account_id=%s', order_account_id, extra={'event': 'protection_sector_emailed'})

    @staticmethod
    def telegram_printer_moderators(order_printer_id: int) -> None:
        ticket = OrderPrinter.objects.get(pk=order_printer_id)
        TelegramSender().send_messages(
            tlg_ids=list(settings.ORDER_PRINTER_MODERATORS_TELEGRAM.values()),
            message=(
                f'Новая заявка!\n\n'
                f'Принтер - {ticket.get_category_display()} #{ticket.id}\n'
                f'Инициатор - {ticket.client}\n'
                f'Адрес - {ticket.address}, каб.{ticket.cabinet}\n'
                f'Телефон - {ticket.phone}\n'
            ),
        )
        logger.info('telegram moderators notified type=printer order_id=%s recipients=%s', order_printer_id, len(settings.ORDER_PRINTER_MODERATORS_TELEGRAM), extra={'event': 'telegram_printer_moderators'})

    @staticmethod
    def telegram_transport_moderators(order_transport_id: int) -> None:
        ticket = OrderTransport.objects.get(pk=order_transport_id)
        TelegramSender().send_messages(
            tlg_ids=list(settings.ORDER_TRANSPORT_MODERATORS_TELEGRAM.values()),
            message=(
                f'Новая заявка!\n\n'
                f'{ticket} #{ticket.id}\n'
                f'Инициатор - {ticket.client}\n'
                f'Телефон - {ticket.phone}\n'
                f'Время - {ticket.transport_arrival_datetime.strftime("%H:%M %d-%m-%y")}\n'
                f'Забрать: {"да" if ticket.comeback else "нет"}'
            ),
        )
        logger.info('telegram moderators notified type=transport order_id=%s recipients=%s', order_transport_id, len(settings.ORDER_TRANSPORT_MODERATORS_TELEGRAM), extra={'event': 'telegram_transport_moderators'})

    @staticmethod
    def telegram_pc_moderators(order_pc_id: int) -> None:
        ticket = OrderPC.objects.get(pk=order_pc_id)
        TelegramSender().send_messages(
            tlg_ids=list(settings.ORDER_PC_MODERATORS_TELEGRAM.values()),
            message=(
                f'Новая заявка!\n\n'
                f'ПК - {ticket.get_category_display()} #{ticket.id}\n'
                f'Инициатор - {ticket.client}\n'
                f'Адрес - {ticket.address}, каб.{ticket.cabinet}\n'
                f'Телефон - {ticket.phone}\n'
            ),
        )
        logger.info('telegram moderators notified type=pc order_id=%s recipients=%s', order_pc_id, len(settings.ORDER_PC_MODERATORS_TELEGRAM), extra={'event': 'telegram_pc_moderators'})

    @staticmethod
    def telegram_aho_moderators(order_aho_id: int) -> None:
        ticket = OrderAho.objects.get(pk=order_aho_id)
        TelegramSender().send_messages(
            tlg_ids=list(settings.ORDER_AHO_MODERATORS_TELEGRAM.values()),
            message=(
                f'Новая заявка!\n\n'
                f'АХО - {ticket.get_category_display()} #{ticket.id}\n'
                f'Инициатор - {ticket.client}\n'
                f'Адрес - {ticket.address}, каб.{ticket.cabinet}\n'
                f'Телефон - {ticket.phone}\n'
            ),
        )
        logger.info('telegram moderators notified type=aho order_id=%s recipients=%s', order_aho_id, len(settings.ORDER_AHO_MODERATORS_TELEGRAM), extra={'event': 'telegram_aho_moderators'})

    @staticmethod
    def telegram_account_moderators(order_account_id: int) -> None:
        ticket = OrderAccount.objects.get(pk=order_account_id)
        desc_line = f'Описание - {ticket.description}\n' if ticket.description else ''
        TelegramSender().send_messages(
            tlg_ids=list(settings.ORDER_ACCOUNT_MODERATORS_TELEGRAM.values()),
            message=(
                f'Новая заявка!\n\n'
                f'Учетная запись - {ticket.get_category_display()} #{ticket.id}\n'
                f'Инициатор - {ticket.client}\n'
                f'Адрес - {ticket.address}, каб.{ticket.cabinet}\n'
                f'Телефон - {ticket.phone}\n'
                f'{desc_line}'
            ),
        )
        logger.info('telegram moderators notified type=account order_id=%s recipients=%s', order_account_id, len(settings.ORDER_ACCOUNT_MODERATORS_TELEGRAM), extra={'event': 'telegram_account_moderators'})

    @staticmethod
    def notify_transport_user(transport_id: int) -> None:
        transport = get_object_or_404(OrderTransport, id=transport_id)
        owner = transport.owner

        if owner.tlg_exists():
            if transport.driver:
                driver_info = f'Автомобиль - {transport.driver.car}\nВодитель - {transport.driver.name} | {transport.driver.phone}\n'
            else:
                driver_info = 'Автомобиль - нет\nВодитель - нет\n'

            departure_datetime = (
                f'{transport.transport_departure_datetime.strftime("%d-%m-%y %H:%M")}\n'
                if transport.transport_departure_datetime
                else 'нет\n'
            )
            departure_location = f'{transport.transport_departure_location}\n' if transport.transport_departure_location else 'нет\n'

            TelegramSender().send_message(
                tlg_id=owner.get_tlg(),
                message=(
                    f'Заявка обновлена!\n\n'
                    f'{transport} #{transport.id}\n'
                    f'{driver_info}'
                    f'Адрес - {departure_location}'
                    f'Время - {departure_datetime}'
                ),
            )
            logger.info('transport user telegram sent transport_id=%s owner_id=%s', transport_id, owner.pk, extra={'event': 'transport_user_telegram_sent'})
        else:
            logger.info('transport user telegram skipped transport_id=%s owner_id=%s reason=no_tlg', transport_id, owner.pk, extra={'event': 'transport_user_telegram_skipped'})

        if owner.mail_exists():
            Mailer().send_messages(
                subject='Заявка обновлена',
                template='orders/email/ordertransport_email_to_user.html',
                context={'object': transport},
                to_emails=[owner.get_email()],
            )
            transport.emailed_to_user = True
            transport.save(update_fields=['emailed_to_user', 'updated_at'])
            logger.info('transport user email sent transport_id=%s owner_id=%s', transport_id, owner.pk, extra={'event': 'transport_user_email_sent'})
        else:
            logger.info('transport user email skipped transport_id=%s owner_id=%s reason=no_email', transport_id, owner.pk, extra={'event': 'transport_user_email_skipped'})

    @staticmethod
    def notify_specialist(object_id, content_type_model: str) -> None:
        user_services.notify_specialist(object_id=object_id, content_type_model=content_type_model)
