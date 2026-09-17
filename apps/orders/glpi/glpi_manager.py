import logging
import os

from apps.orders.glpi import glpi_api


logger = logging.getLogger('adm.integrations.glpi')

GLPI_APP_TOKEN = os.getenv('GLPI_APP_TOKEN')
GLPI_USER_TOKEN = os.getenv('GLPI_USER_TOKEN')
GLPI_API_URL = os.getenv('GLPI_API_URL')


class TicketStatus:
    open = 2
    closed = 6


def _connect():
    if not all([GLPI_API_URL, GLPI_APP_TOKEN, GLPI_USER_TOKEN]):
        raise RuntimeError('GLPI integration is not configured via environment variables')
    return glpi_api.connect(url=GLPI_API_URL, apptoken=GLPI_APP_TOKEN, auth=GLPI_USER_TOKEN)


def get_ticket(ticket_id: int):
    try:
        with _connect() as glpi:
            result = glpi.get_item('Ticket', ticket_id)
            logger.info('glpi ticket fetched ticket_id=%s', ticket_id, extra={'event': 'glpi_ticket_fetched'})
            return result
    except glpi_api.GLPIError:
        logger.exception('glpi ticket fetch failed ticket_id=%s', ticket_id)
        raise


def ticket_create(printer):
    text_data = f"""

        Клиент: {printer.client}
        Принтер: {printer.printer_name}
        Адрес: {printer.address} кабинет №{printer.cabinet}. тел. {printer.phone}
        Комментарий:
        {printer.description}
        """
    ticket_payload = {
        'name': f'Принтер-{printer.get_printer_category_display().lower()}',
        'status': TicketStatus.open,
        'content': text_data,
        'itilcategories_id': 1,
    }
    try:
        with _connect() as glpi:
            result = glpi.add('ticket', ticket_payload)
            ticket_id = int(result[0].get('id', 0))
            logger.info('glpi ticket created printer_id=%s glpi_ticket_id=%s', printer.id, ticket_id, extra={'event': 'glpi_ticket_created'})
            return ticket_id
    except glpi_api.GLPIError:
        logger.exception('glpi ticket create failed printer_id=%s', getattr(printer, 'id', '-'))
        raise


def ticket_update(items: dict):
    try:
        with _connect() as glpi:
            result = glpi.update('ticket', items)
            logger.info('glpi ticket updated payload_size=%s', len(items or {}), extra={'event': 'glpi_ticket_updated'})
            return result
    except glpi_api.GLPIError:
        logger.exception('glpi ticket update failed')
        raise


def item_list_options(itemname: str):
    try:
        with _connect() as glpi:
            result = glpi.list_search_options(itemname)
            logger.info('glpi item list options fetched itemname=%s', itemname, extra={'event': 'glpi_item_options_fetched'})
            return result
    except glpi_api.GLPIError:
        logger.exception('glpi item list options failed itemname=%s', itemname)
        raise
