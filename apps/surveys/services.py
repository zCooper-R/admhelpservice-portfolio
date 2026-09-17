import logging

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.surveys.models import (
    SurveyAnswer,
    SurveyAnswerOptionSelection,
    SurveyQuestion,
    SurveySubmission,
)
from apps.surveys.selectors import get_current_active_campaign, user_has_submission_for_campaign


logger = logging.getLogger('adm.apps.surveys')


class SurveyError(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.message = message
        self.errors = errors or {}


def _extract_validation_messages(exc):
    if hasattr(exc, 'message_dict'):
        messages = []
        for field_messages in exc.message_dict.values():
            messages.extend(field_messages)
        if messages:
            return messages
    if hasattr(exc, 'messages'):
        return list(exc.messages)
    return ['Ответ не прошёл валидацию.']


def campaign_to_popup_payload(campaign):
    return {
        'id': campaign.id,
        'title': campaign.title,
        'slug': campaign.slug,
        'description': campaign.description,
        'popup_title': campaign.popup_title,
        'popup_text': campaign.popup_text,
        'question_count': getattr(campaign, 'question_count', campaign.questions.count()),
        'questions': [
            {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'options': [
                    {
                        'id': option.id,
                        'text': option.text,
                        'value': option.value,
                        'order': option.order,
                    }
                    for option in question.options.all()
                ],
            }
            for question in campaign.questions.all()
        ],
    }


def get_popup_state_for_user(user):
    if not user.is_authenticated:
        return {'show': False}

    campaign = get_current_active_campaign()
    if campaign is None:
        logger.debug('survey popup hidden user_id=%s reason=no_active_campaign', user.pk)
        return {'show': False}

    if user_has_submission_for_campaign(user, campaign):
        logger.info('survey popup hidden user_id=%s campaign_id=%s reason=already_submitted', user.pk, campaign.id)
        return {'show': False}

    logger.info('survey popup available user_id=%s campaign_id=%s', user.pk, campaign.id, extra={'event': 'survey_popup_available'})
    return {
        'show': True,
        'campaign': campaign_to_popup_payload(campaign),
    }


def _question_map_for_campaign(campaign):
    questions = list(campaign.questions.all())
    if not questions:
        raise SurveyError('Нельзя показывать кампанию без вопросов.')
    return {question.id: question for question in questions}


def _normalize_answers_map(raw_answers):
    answers_by_question = {}
    for item in raw_answers:
        if not isinstance(item, dict):
            raise SurveyError('Каждый ответ должен быть объектом.', errors={'answers': ['Некорректный формат ответа.']})

        question_id = item.get('question_id')
        if not question_id:
            raise SurveyError('В ответе отсутствует question_id.', errors={'answers': ['У одного из ответов нет question_id.']})

        if question_id in answers_by_question:
            raise SurveyError(
                'Нельзя передавать несколько ответов на один и тот же вопрос.',
                errors={str(question_id): ['Обнаружены дубли ответов по одному вопросу.']},
            )
        answers_by_question[question_id] = item
    return answers_by_question


def _validate_required_questions(question_map, answers_by_question):
    errors = {}
    for question in question_map.values():
        payload = answers_by_question.get(question.id)
        if question.is_required and not payload:
            errors[str(question.id)] = ['Это обязательный вопрос.']
    return errors


def _validate_option_ids(question, option_ids):
    valid_option_ids = set(question.options.values_list('id', flat=True))
    if not set(option_ids).issubset(valid_option_ids):
        raise SurveyError(
            'Обнаружен вариант ответа от другого вопроса.',
            errors={str(question.id): ['Выбран недопустимый вариант ответа.']},
        )


def submit_campaign_answers(*, campaign, user, raw_answers):
    if not user.is_authenticated:
        raise SurveyError('Отправка доступна только авторизованным пользователям.')

    if not campaign.is_currently_active:
        raise SurveyError('Кампания сейчас неактивна.')

    question_map = _question_map_for_campaign(campaign)
    answers_by_question = _normalize_answers_map(raw_answers)
    errors = _validate_required_questions(question_map, answers_by_question)

    unknown_question_ids = set(answers_by_question.keys()) - set(question_map.keys())
    if unknown_question_ids:
        raise SurveyError(
            'Обнаружены вопросы из другой кампании.',
            errors={'answers': ['В запросе есть вопросы, не принадлежащие кампании.']},
        )

    prepared_answers = []
    for question in question_map.values():
        payload = answers_by_question.get(question.id)
        if not payload:
            continue

        if question.question_type == SurveyQuestion.QuestionType.RATING:
            rating_value = payload.get('rating_value')
            if rating_value in ('', None):
                if question.is_required:
                    errors.setdefault(str(question.id), []).append('Укажите оценку от 1 до 5.')
                continue
            try:
                rating_value = int(rating_value)
            except (TypeError, ValueError):
                errors.setdefault(str(question.id), []).append('Оценка должна быть числом от 1 до 5.')
                continue
            if rating_value < 1 or rating_value > 5:
                errors.setdefault(str(question.id), []).append('Оценка должна быть в диапазоне от 1 до 5.')
                continue
            prepared_answers.append({
                'question': question,
                'rating_value': rating_value,
                'text_answer': '',
                'selected_option_id': None,
                'multiple_option_ids': [],
            })

        elif question.question_type == SurveyQuestion.QuestionType.TEXT:
            text_answer = (payload.get('text_answer') or '').strip()
            if question.is_required and not text_answer:
                errors.setdefault(str(question.id), []).append('Текстовый ответ обязателен.')
                continue
            if not text_answer:
                continue
            prepared_answers.append({
                'question': question,
                'rating_value': None,
                'text_answer': text_answer,
                'selected_option_id': None,
                'multiple_option_ids': [],
            })

        elif question.question_type == SurveyQuestion.QuestionType.SINGLE_CHOICE:
            option_id = payload.get('selected_option_id')
            if option_id in ('', None):
                if question.is_required:
                    errors.setdefault(str(question.id), []).append('Выберите один из вариантов ответа.')
                continue
            try:
                option_id = int(option_id)
            except (TypeError, ValueError):
                errors.setdefault(str(question.id), []).append('Некорректный вариант ответа.')
                continue
            try:
                _validate_option_ids(question, [option_id])
            except SurveyError as exc:
                errors.setdefault(str(question.id), []).extend(exc.errors.get(str(question.id), [exc.message]))
                continue
            prepared_answers.append({
                'question': question,
                'rating_value': None,
                'text_answer': '',
                'selected_option_id': option_id,
                'multiple_option_ids': [],
            })

        elif question.question_type == SurveyQuestion.QuestionType.MULTIPLE_CHOICE:
            option_ids = payload.get('selected_option_ids') or []
            if not isinstance(option_ids, list):
                errors.setdefault(str(question.id), []).append('Выбранные варианты должны быть массивом.')
                continue
            try:
                normalized_ids = [int(value) for value in option_ids]
            except (TypeError, ValueError):
                errors.setdefault(str(question.id), []).append('Некорректный список вариантов ответа.')
                continue
            if question.is_required and not normalized_ids:
                errors.setdefault(str(question.id), []).append('Нужно выбрать хотя бы один вариант.')
                continue
            try:
                _validate_option_ids(question, normalized_ids)
            except SurveyError as exc:
                errors.setdefault(str(question.id), []).extend(exc.errors.get(str(question.id), [exc.message]))
                continue
            prepared_answers.append({
                'question': question,
                'rating_value': None,
                'text_answer': '',
                'selected_option_id': None,
                'multiple_option_ids': normalized_ids,
            })

    if errors:
        logger.info(
            'survey submission rejected user_id=%s campaign_id=%s validation_errors=%s',
            user.pk,
            campaign.id,
            sorted(errors.keys()),
            extra={'event': 'survey_submission_rejected'},
        )
        raise SurveyError('Форма заполнена с ошибками.', errors=errors)

    if not prepared_answers:
        raise SurveyError(
            'Нельзя отправить пустой опрос.',
            errors={'answers': ['Нужно ответить хотя бы на один вопрос.']},
        )

    try:
        with transaction.atomic():
            submission = SurveySubmission.objects.create(
                campaign=campaign,
                user=user,
                submitted_at=timezone.now(),
            )
            for item in prepared_answers:
                answer = SurveyAnswer(
                    submission=submission,
                    question=item['question'],
                    text_answer=item['text_answer'],
                    rating_value=item['rating_value'],
                    selected_option_id=item['selected_option_id'],
                )
                try:
                    answer.full_clean()
                except ValidationError as exc:
                    logger.info(
                        'survey answer validation rejected user_id=%s campaign_id=%s question_id=%s',
                        user.pk,
                        campaign.id,
                        item['question'].id,
                        extra={'event': 'survey_answer_validation_rejected'},
                    )
                    raise SurveyError(
                        'Форма заполнена с ошибками.',
                        errors={str(item['question'].id): _extract_validation_messages(exc)},
                    )
                answer.save()

                if item['multiple_option_ids']:
                    selections = [
                        SurveyAnswerOptionSelection(answer=answer, option_id=option_id)
                        for option_id in item['multiple_option_ids']
                    ]
                    for selection in selections:
                        try:
                            selection.full_clean()
                        except ValidationError as exc:
                            logger.info(
                                'survey answer option validation rejected user_id=%s campaign_id=%s question_id=%s',
                                user.pk,
                                campaign.id,
                                item['question'].id,
                                extra={'event': 'survey_answer_option_validation_rejected'},
                            )
                            raise SurveyError(
                                'Форма заполнена с ошибками.',
                                errors={str(item['question'].id): _extract_validation_messages(exc)},
                            )
                    SurveyAnswerOptionSelection.objects.bulk_create(selections)

            logger.info(
                'survey submission created user_id=%s campaign_id=%s submission_id=%s answers=%s',
                user.pk,
                campaign.id,
                submission.id,
                len(prepared_answers),
                extra={'event': 'survey_submission_created'},
            )
            return submission
    except IntegrityError:
        logger.warning(
            'survey submission duplicate user_id=%s campaign_id=%s',
            user.pk,
            campaign.id,
            extra={'event': 'survey_submission_duplicate'},
        )
        raise SurveyError(
            'Вы уже отправили ответы по этой кампании.',
            errors={'submission': ['Повторная отправка для этой кампании запрещена.']},
        )
    except ValidationError as exc:
        logger.exception('survey submission validation exception user_id=%s campaign_id=%s', user.pk, campaign.id)
        raise SurveyError('Форма заполнена с ошибками.', errors={'answers': _extract_validation_messages(exc)})
