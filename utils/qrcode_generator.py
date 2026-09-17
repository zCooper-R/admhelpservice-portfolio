import qrcode
from io import BytesIO

from django.conf import settings
from django.core.files import File

import logging

from utils.util import encode_string

logger = logging.getLogger(__name__)


def generate_qr_code(user):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    encoded_command = encode_string(f'tlgid-{user.username}')
    qr.add_data(f'{settings.TELEGRAM_BOT_LINK}?start={encoded_command}')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer)
    filename = f'qr_{user.username}.png'
    user.telegram_qrcode.save(filename, File(buffer), save=True)
    logger.info('qr code generated user_id=%s', user.pk, extra={'event': 'qr_code_generated'})
