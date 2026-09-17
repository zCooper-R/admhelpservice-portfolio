import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.surveys.models import (
    SurveyAnswer,
    SurveyAnswerOptionSelection,
    SurveyCampaign,
    SurveyOption,
    SurveyQuestion,
    SurveySubmission,
)
from apps.surveys.services import get_popup_state_for_user


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username='survey-user', password='test-pass')


@pytest.fixture
def active_campaign(db):
    campaign = SurveyCampaign.objects.create(
        title='Spring Wave',
        slug='spring-wave',
        is_active=True,
        popup_title='Оцените сервис',
        popup_text='Это короткий опрос о работе сервиса.',
        starts_at=timezone.now() - timedelta(days=1),
        ends_at=timezone.now() + timedelta(days=1),
    )
    SurveyQuestion.objects.create(
        campaign=campaign,
        text='Как вы оцениваете сервис в целом?',
        question_type=SurveyQuestion.QuestionType.RATING,
        is_required=True,
        order=1,
    )
    SurveyQuestion.objects.create(
        campaign=campaign,
        text='Что можно улучшить?',
        question_type=SurveyQuestion.QuestionType.TEXT,
        is_required=False,
        order=2,
    )
    single_choice_question = SurveyQuestion.objects.create(
        campaign=campaign,
        text='Насколько удобно пользоваться сервисом?',
        question_type=SurveyQuestion.QuestionType.SINGLE_CHOICE,
        is_required=True,
        order=3,
    )
    multi_choice_question = SurveyQuestion.objects.create(
        campaign=campaign,
        text='Какие стороны сервиса вам понравились?',
        question_type=SurveyQuestion.QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order=4,
    )

    SurveyOption.objects.bulk_create(
        [
            SurveyOption(question=single_choice_question, text='Очень удобно', value='very-good', order=1),
            SurveyOption(question=single_choice_question, text='Нормально', value='normal', order=2),
            SurveyOption(question=multi_choice_question, text='Скорость', value='speed', order=1),
            SurveyOption(question=multi_choice_question, text='Понятный интерфейс', value='ui', order=2),
        ]
    )
    return campaign


@pytest.mark.django_db
def test_campaign_currently_active_property(active_campaign):
    assert active_campaign.is_currently_active is True


@pytest.mark.django_db
def test_popup_is_shown_only_if_user_has_not_answered(user, active_campaign):
    state = get_popup_state_for_user(user)
    assert state['show'] is True

    SurveySubmission.objects.create(campaign=active_campaign, user=user)
    state = get_popup_state_for_user(user)
    assert state['show'] is False


@pytest.mark.django_db
def test_popup_hidden_for_campaign_without_questions(user):
    SurveyCampaign.objects.create(
        title='Empty campaign',
        slug='empty-campaign',
        is_active=True,
        popup_title='Опрос',
        popup_text='Пустой опрос',
        starts_at=timezone.now() - timedelta(days=1),
        ends_at=timezone.now() + timedelta(days=1),
    )

    state = get_popup_state_for_user(user)
    assert state['show'] is False


@pytest.mark.django_db
def test_current_popup_endpoint_returns_active_campaign(client, user, active_campaign):
    client.force_login(user)
    response = client.get(reverse('surveys:current_popup'))

    assert response.status_code == 200
    payload = response.json()
    assert payload['show'] is True
    assert payload['campaign']['id'] == active_campaign.id
    assert payload['campaign']['question_count'] == 4


@pytest.mark.django_db
def test_popup_not_shown_after_successful_submission(client, user, active_campaign):
    client.force_login(user)
    single_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.SINGLE_CHOICE)
    multiple_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.MULTIPLE_CHOICE)
    single_choice_option = single_choice_question.options.order_by('order').first()
    multi_choice_options = list(multiple_choice_question.options.order_by('order').values_list('id', flat=True))

    response = client.post(
        reverse('surveys:submit_popup'),
        data=json.dumps(
            {
                'campaign_id': active_campaign.id,
                'answers': [
                    {
                        'question_id': active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.RATING).id,
                        'rating_value': 5,
                    },
                    {
                        'question_id': active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.TEXT).id,
                        'text_answer': 'Отличная работа',
                    },
                    {
                        'question_id': single_choice_question.id,
                        'selected_option_id': single_choice_option.id,
                    },
                    {
                        'question_id': multiple_choice_question.id,
                        'selected_option_ids': multi_choice_options,
                    },
                ],
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 200
    assert response.json()['success'] is True
    assert SurveySubmission.objects.filter(campaign=active_campaign, user=user).count() == 1

    popup_response = client.get(reverse('surveys:current_popup'))
    assert popup_response.status_code == 200
    assert popup_response.json()['show'] is False


@pytest.mark.django_db
def test_user_cannot_submit_twice(client, user, active_campaign):
    client.force_login(user)
    rating_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.RATING)
    single_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.SINGLE_CHOICE)
    multiple_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.MULTIPLE_CHOICE)

    payload = {
        'campaign_id': active_campaign.id,
        'answers': [
            {'question_id': rating_question.id, 'rating_value': 4},
            {
                'question_id': single_choice_question.id,
                'selected_option_id': single_choice_question.options.order_by('order').first().id,
            },
            {
                'question_id': multiple_choice_question.id,
                'selected_option_ids': list(multiple_choice_question.options.values_list('id', flat=True)),
            },
        ],
    }
    first_response = client.post(reverse('surveys:submit_popup'), data=json.dumps(payload), content_type='application/json')
    second_response = client.post(reverse('surveys:submit_popup'), data=json.dumps(payload), content_type='application/json')

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert SurveySubmission.objects.filter(campaign=active_campaign, user=user).count() == 1


@pytest.mark.django_db
def test_submission_rejects_option_from_another_question(client, user, active_campaign):
    client.force_login(user)
    rating_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.RATING)
    single_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.SINGLE_CHOICE)
    multiple_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.MULTIPLE_CHOICE)
    foreign_option = multiple_choice_question.options.order_by('order').first()

    response = client.post(
        reverse('surveys:submit_popup'),
        data=json.dumps(
            {
                'campaign_id': active_campaign.id,
                'answers': [
                    {'question_id': rating_question.id, 'rating_value': 4},
                    {'question_id': single_choice_question.id, 'selected_option_id': foreign_option.id},
                    {'question_id': multiple_choice_question.id, 'selected_option_ids': [foreign_option.id]},
                ],
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'Выбран недопустимый вариант ответа.' in ' '.join(response.json()['errors'][str(single_choice_question.id)])


@pytest.mark.django_db
def test_required_questions_are_validated(client, user, active_campaign):
    client.force_login(user)
    response = client.post(
        reverse('surveys:submit_popup'),
        data=json.dumps(
            {
                'campaign_id': active_campaign.id,
                'answers': [],
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 400
    errors = response.json()['errors']
    assert str(active_campaign.questions.get(order=1).id) in errors
    assert str(active_campaign.questions.get(order=3).id) in errors
    assert str(active_campaign.questions.get(order=4).id) in errors


@pytest.mark.django_db
def test_submission_creates_answers_for_all_supported_types(client, user, active_campaign):
    client.force_login(user)
    rating_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.RATING)
    text_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.TEXT)
    single_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.SINGLE_CHOICE)
    multiple_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.MULTIPLE_CHOICE)

    single_choice_option = single_choice_question.options.order_by('order').first()
    multiple_choice_option_ids = list(multiple_choice_question.options.order_by('order').values_list('id', flat=True))

    response = client.post(
        reverse('surveys:submit_popup'),
        data=json.dumps(
            {
                'campaign_id': active_campaign.id,
                'answers': [
                    {'question_id': rating_question.id, 'rating_value': 5},
                    {'question_id': text_question.id, 'text_answer': 'Все отлично'},
                    {'question_id': single_choice_question.id, 'selected_option_id': single_choice_option.id},
                    {'question_id': multiple_choice_question.id, 'selected_option_ids': multiple_choice_option_ids},
                ],
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 200

    submission = SurveySubmission.objects.get(campaign=active_campaign, user=user)
    assert submission.answers.count() == 4
    assert SurveyAnswer.objects.get(submission=submission, question=rating_question).rating_value == 5
    assert SurveyAnswer.objects.get(submission=submission, question=text_question).text_answer == 'Все отлично'
    assert SurveyAnswer.objects.get(submission=submission, question=single_choice_question).selected_option_id == single_choice_option.id

    multiple_answer = SurveyAnswer.objects.get(submission=submission, question=multiple_choice_question)
    assert SurveyAnswerOptionSelection.objects.filter(answer=multiple_answer).count() == 2


@pytest.mark.django_db
def test_optional_text_question_can_be_left_empty(client, user, active_campaign):
    client.force_login(user)
    rating_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.RATING)
    single_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.SINGLE_CHOICE)
    multiple_choice_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.MULTIPLE_CHOICE)
    text_question = active_campaign.questions.get(question_type=SurveyQuestion.QuestionType.TEXT)

    response = client.post(
        reverse('surveys:submit_popup'),
        data=json.dumps(
            {
                'campaign_id': active_campaign.id,
                'answers': [
                    {'question_id': rating_question.id, 'rating_value': 5},
                    {'question_id': text_question.id, 'text_answer': ''},
                    {
                        'question_id': single_choice_question.id,
                        'selected_option_id': single_choice_question.options.order_by('order').first().id,
                    },
                    {
                        'question_id': multiple_choice_question.id,
                        'selected_option_ids': list(multiple_choice_question.options.order_by('order').values_list('id', flat=True)),
                    },
                ],
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 200

    submission = SurveySubmission.objects.get(campaign=active_campaign, user=user)
    assert submission.answers.filter(question=text_question).count() == 0


@pytest.mark.django_db
def test_submit_popup_rejects_invalid_json(client, user, active_campaign):
    client.force_login(user)
    response = client.post(
        reverse('surveys:submit_popup'),
        data='{invalid json',
        content_type='application/json',
    )

    assert response.status_code == 400
    assert response.json()['success'] is False
