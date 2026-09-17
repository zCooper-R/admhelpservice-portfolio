from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

import logging

from utils.qrcode_generator import generate_qr_code
from utils.util import encode_string

logger = logging.getLogger(__name__)


class QrCodeTelegramBotView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/qrcode_telegram_bot.html'

    def render_to_response(self, context, **response_kwargs):
        logger.info(f'{self.request.user}')
        if not bool(self.request.user.telegram_qrcode):
            logger.info('QRCODE not found, creating...')
            generate_qr_code(user=self.request.user)
        context['tlg_command'] = encode_string(f'tlgid-{self.request.user.username}')
        return render(self.request, template_name='orders/qrcode_telegram_bot.html', context=context)
