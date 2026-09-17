import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.surveys.forms import SurveySubmissionRequestForm
from apps.surveys.models import SurveyCampaign
from apps.surveys.services import SurveyError, get_popup_state_for_user, submit_campaign_answers


logger = logging.getLogger('adm.apps.surveys')


class CurrentSurveyPopupView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        payload = get_popup_state_for_user(request.user)
        logger.debug(
            'survey current_popup requested user_id=%s show=%s',
            request.user.pk,
            payload.get('show', False),
        )
        return JsonResponse(payload)


class SubmitSurveyPopupView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning(
                'survey submit rejected user_id=%s reason=invalid_json',
                request.user.pk,
                extra={'event': 'survey_submit_invalid_json'},
            )
            return JsonResponse(
                {'success': False, 'message': 'Ожидался корректный JSON.'},
                status=400,
            )

        form = SurveySubmissionRequestForm(payload)
        if not form.is_valid():
            logger.info(
                'survey submit rejected user_id=%s reason=form_invalid',
                request.user.pk,
                extra={'event': 'survey_submit_invalid_form'},
            )
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Форма заполнена с ошибками.',
                    'errors': form.errors,
                },
                status=400,
            )

        campaign = get_object_or_404(
            SurveyCampaign.objects.prefetch_related('questions__options'),
            pk=form.cleaned_data['campaign_id'],
        )

        try:
            submission = submit_campaign_answers(
                campaign=campaign,
                user=request.user,
                raw_answers=form.cleaned_data['answers'],
            )
        except SurveyError as exc:
            logger.info(
                'survey submit failed user_id=%s campaign_id=%s error_keys=%s',
                request.user.pk,
                campaign.id,
                sorted((exc.errors or {}).keys()),
                extra={'event': 'survey_submit_failed'},
            )
            return JsonResponse(
                {'success': False, 'message': exc.message, 'errors': exc.errors},
                status=400,
            )

        return JsonResponse(
            {
                'success': True,
                'message': 'Спасибо, ваш ответ сохранён.',
                'submission_id': submission.id,
            }
        )
