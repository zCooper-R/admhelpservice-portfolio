from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Q
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")

    class Meta:
        abstract = True


class SurveyCampaignQuerySet(models.QuerySet):
    def active_now(self, at=None):
        at = at or timezone.now()
        return self.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=at),
            Q(ends_at__isnull=True) | Q(ends_at__gte=at),
        )


class SurveyCampaign(TimeStampedModel):
    objects = SurveyCampaignQuerySet.as_manager()

    title = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=False, verbose_name="Активна")
    starts_at = models.DateTimeField(blank=True, null=True, verbose_name="Показывать с")
    ends_at = models.DateTimeField(blank=True, null=True, verbose_name="Показывать до")
    popup_title = models.CharField(max_length=255, verbose_name="Заголовок popup")
    popup_text = models.TextField(blank=True, verbose_name="Текст popup")
    priority = models.PositiveSmallIntegerField(default=100, verbose_name="Приоритет")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_survey_campaigns",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Создал",
    )

    class Meta:
        verbose_name = "Кампания опроса"
        verbose_name_plural = "Кампании опросов"
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "starts_at", "ends_at"], name="srv_camp_active_idx"),
            models.Index(fields=["priority", "created_at"], name="srv_camp_prio_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValidationError({"ends_at": "Дата окончания не может быть раньше даты начала."})

        if not self.slug:
            self.slug = slugify(self.title)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_currently_active(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True

    def get_submission_count(self):
        return getattr(self, "submission_count", None) or self.submissions.count()

    def get_average_rating(self):
        annotated_value = getattr(self, "average_rating", None)
        if annotated_value is not None:
            return annotated_value
        return SurveyAnswer.objects.filter(
            question__campaign=self,
            rating_value__isnull=False,
        ).aggregate(avg=Avg("rating_value"))["avg"]


class SurveyQuestion(TimeStampedModel):
    class QuestionType(models.TextChoices):
        RATING = "rating", "Оценка 1-5"
        SINGLE_CHOICE = "single_choice", "Один вариант"
        MULTIPLE_CHOICE = "multiple_choice", "Несколько вариантов"
        TEXT = "text", "Текст"

    campaign = models.ForeignKey(
        SurveyCampaign,
        related_name="questions",
        on_delete=models.CASCADE,
        verbose_name="Кампания",
    )
    text = models.TextField(verbose_name="Текст вопроса")
    question_type = models.CharField(
        max_length=32,
        choices=QuestionType.choices,
        verbose_name="Тип вопроса",
    )
    is_required = models.BooleanField(default=True, verbose_name="Обязательный")
    order = models.PositiveSmallIntegerField(default=1, verbose_name="Порядок")

    class Meta:
        verbose_name = "Вопрос кампании"
        verbose_name_plural = "Вопросы кампаний"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "order"], name="srv_q_campaign_order_uq"),
        ]

    def __str__(self):
        return f"{self.campaign}: {self.text[:60]}"


class SurveyOption(TimeStampedModel):
    question = models.ForeignKey(
        SurveyQuestion,
        related_name="options",
        on_delete=models.CASCADE,
        verbose_name="Вопрос",
    )
    text = models.CharField(max_length=255, verbose_name="Текст варианта")
    value = models.CharField(max_length=64, blank=True, verbose_name="Техническое значение")
    order = models.PositiveSmallIntegerField(default=1, verbose_name="Порядок")

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответа"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "order"], name="srv_opt_question_order_uq"),
            models.UniqueConstraint(fields=["question", "value"], name="srv_opt_question_value_uq"),
        ]

    def __str__(self):
        return self.text

    def clean(self):
        super().clean()
        if self.question.question_type not in {
            SurveyQuestion.QuestionType.SINGLE_CHOICE,
            SurveyQuestion.QuestionType.MULTIPLE_CHOICE,
        }:
            raise ValidationError("Варианты ответа допустимы только для вопросов с выбором.")

        if not self.value:
            self.value = slugify(self.text)[:64] or f"option-{self.order}"

    def save(self, *args, **kwargs):
        if not self.value:
            self.value = slugify(self.text)[:64] or f"option-{self.order}"
        self.full_clean()
        return super().save(*args, **kwargs)


class SurveySubmission(TimeStampedModel):
    campaign = models.ForeignKey(
        SurveyCampaign,
        related_name="submissions",
        on_delete=models.CASCADE,
        verbose_name="Кампания",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="survey_submissions",
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    submitted_at = models.DateTimeField(default=timezone.now, verbose_name="Отправлено")

    class Meta:
        verbose_name = "Прохождение опроса"
        verbose_name_plural = "Прохождения опросов"
        ordering = ["-submitted_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "user"], name="srv_sub_campaign_user_uq"),
        ]
        indexes = [
            models.Index(fields=["campaign", "submitted_at"], name="srv_sub_campaign_idx"),
            models.Index(fields=["user", "submitted_at"], name="srv_sub_user_idx"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.campaign}"


class SurveyAnswer(TimeStampedModel):
    submission = models.ForeignKey(
        SurveySubmission,
        related_name="answers",
        on_delete=models.CASCADE,
        verbose_name="Прохождение",
    )
    question = models.ForeignKey(
        SurveyQuestion,
        related_name="answers",
        on_delete=models.CASCADE,
        verbose_name="Вопрос",
    )
    text_answer = models.TextField(blank=True, verbose_name="Текстовый ответ")
    selected_option = models.ForeignKey(
        SurveyOption,
        related_name="single_choice_answers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Выбранный вариант",
    )
    rating_value = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Оценка",
    )

    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"
        ordering = ["question__order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["submission", "question"], name="srv_answer_sub_question_uq"),
            models.CheckConstraint(
                condition=Q(rating_value__isnull=True) | (Q(rating_value__gte=1) & Q(rating_value__lte=5)),
                name="srv_answer_rating_range_ck",
            ),
        ]

    def __str__(self):
        return f"{self.submission} / {self.question}"

    def clean(self):
        super().clean()
        if self.question.campaign_id != self.submission.campaign_id:
            raise ValidationError("Вопрос должен относиться к той же кампании, что и submission.")

        if self.selected_option and self.selected_option.question_id != self.question_id:
            raise ValidationError({"selected_option": "Нельзя выбрать вариант от другого вопроса."})

        if self.question.question_type == SurveyQuestion.QuestionType.RATING:
            if self.rating_value is None:
                raise ValidationError({"rating_value": "Для rating-вопроса нужна оценка."})
            if self.selected_option_id or self.text_answer:
                raise ValidationError("Rating-вопрос не должен содержать текст или выбранный option.")

        if self.question.question_type == SurveyQuestion.QuestionType.TEXT:
            if not self.text_answer.strip():
                raise ValidationError({"text_answer": "Для текстового вопроса нужен текстовый ответ."})
            if self.selected_option_id or self.rating_value is not None:
                raise ValidationError("Текстовый вопрос не должен содержать оценку или option.")

        if self.question.question_type == SurveyQuestion.QuestionType.SINGLE_CHOICE:
            if not self.selected_option_id:
                raise ValidationError({"selected_option": "Для вопроса с одним выбором нужен option."})
            if self.text_answer or self.rating_value is not None:
                raise ValidationError("Single choice вопрос не должен содержать текст или оценку.")

        if self.question.question_type == SurveyQuestion.QuestionType.MULTIPLE_CHOICE:
            if self.text_answer or self.rating_value is not None or self.selected_option_id:
                raise ValidationError("Multiple choice вопрос хранит выборы только через отдельную модель связей.")


class SurveyAnswerOptionSelection(TimeStampedModel):
    answer = models.ForeignKey(
        SurveyAnswer,
        related_name="selected_options",
        on_delete=models.CASCADE,
        verbose_name="Ответ",
    )
    option = models.ForeignKey(
        SurveyOption,
        related_name="multiple_choice_selections",
        on_delete=models.CASCADE,
        verbose_name="Вариант",
    )

    class Meta:
        verbose_name = "Выбранный вариант multiple choice"
        verbose_name_plural = "Выбранные варианты multiple choice"
        constraints = [
            models.UniqueConstraint(fields=["answer", "option"], name="srv_answer_option_sel_uq"),
        ]

    def __str__(self):
        return f"{self.answer} -> {self.option}"

    def clean(self):
        super().clean()
        if self.option.question_id != self.answer.question_id:
            raise ValidationError({"option": "Нельзя выбрать вариант от другого вопроса."})
