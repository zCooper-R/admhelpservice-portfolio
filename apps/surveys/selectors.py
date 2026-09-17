from django.db.models import Avg, Count, Prefetch

from apps.surveys.models import SurveyCampaign, SurveyOption, SurveyQuestion, SurveySubmission


def _campaign_with_questions_queryset():
    question_qs = SurveyQuestion.objects.order_by('order', 'id').prefetch_related(
        Prefetch('options', queryset=SurveyOption.objects.order_by('order', 'id'))
    )
    return (
        SurveyCampaign.objects.active_now()
        .prefetch_related(Prefetch('questions', queryset=question_qs))
        .annotate(
            submission_count=Count('submissions', distinct=True),
            average_rating=Avg('questions__answers__rating_value'),
            question_count=Count('questions', distinct=True),
        )
        .order_by('-priority', '-created_at')
    )


def get_current_active_campaign():
    return _campaign_with_questions_queryset().filter(question_count__gt=0).first()


def user_has_submission_for_campaign(user, campaign):
    return SurveySubmission.objects.filter(user=user, campaign=campaign).exists()
