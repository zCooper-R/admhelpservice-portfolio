from django.contrib import admin
from django.db.models import Avg, Count
from django.utils.html import format_html

from apps.surveys.models import (
    SurveyAnswer,
    SurveyAnswerOptionSelection,
    SurveyCampaign,
    SurveyOption,
    SurveyQuestion,
    SurveySubmission,
)


class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 0
    fields = ('order', 'text', 'question_type', 'is_required')
    ordering = ('order', 'id')


class SurveyAnswerInline(admin.TabularInline):
    model = SurveyAnswer
    extra = 0
    can_delete = False
    fields = ('question', 'rating_value', 'selected_option', 'text_answer', 'render_selected_options')
    readonly_fields = ('question', 'rating_value', 'selected_option', 'text_answer', 'render_selected_options')

    @admin.display(description='Multiple choice')
    def render_selected_options(self, obj):
        options = obj.selected_options.select_related('option').values_list('option__text', flat=True)
        return ', '.join(options) or '—'


@admin.register(SurveyCampaign)
class SurveyCampaignAdmin(admin.ModelAdmin):
    inlines = [SurveyQuestionInline]
    list_display = (
        'title',
        'is_active',
        'active_window',
        'priority',
        'question_total',
        'submission_total',
        'average_rating_value',
        'created_by',
        'created_at',
    )
    list_display_links = ('title',)
    list_filter = ('is_active', 'priority', 'starts_at', 'ends_at', 'created_at')
    search_fields = ('title', 'slug', 'description', 'popup_title', 'popup_text')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('question_total', 'submission_total', 'average_rating_value', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'description', 'is_active', 'priority', 'created_by')}),
        ('Popup', {'fields': ('popup_title', 'popup_text', ('starts_at', 'ends_at'))}),
        ('Аналитика', {'fields': ('question_total', 'submission_total', 'average_rating_value', 'created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            _question_total=Count('questions', distinct=True),
            _submission_total=Count('submissions', distinct=True),
            _average_rating_value=Avg('questions__answers__rating_value'),
        )

    @admin.display(description='Статус')
    def active_window(self, obj):
        if obj.is_currently_active:
            return format_html('<span style="color:#198754;">Активна сейчас</span>')
        return format_html('<span style="color:#6c757d;">Неактивна</span>')

    @admin.display(description='Вопросов', ordering='_question_total')
    def question_total(self, obj):
        return getattr(obj, '_question_total', 0)

    @admin.display(description='Ответов', ordering='_submission_total')
    def submission_total(self, obj):
        return getattr(obj, '_submission_total', 0)

    @admin.display(description='Средняя оценка', ordering='_average_rating_value')
    def average_rating_value(self, obj):
        value = getattr(obj, '_average_rating_value', None)
        return f'{value:.2f}' if value is not None else '—'

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'order', 'question_type', 'is_required', 'option_total', 'short_text')
    list_filter = ('question_type', 'is_required', 'campaign')
    search_fields = ('text', 'campaign__title')
    ordering = ('campaign', 'order', 'id')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_option_total=Count('options', distinct=True))

    @admin.display(description='Вопрос')
    def short_text(self, obj):
        return obj.text[:100]

    @admin.display(description='Опций', ordering='_option_total')
    def option_total(self, obj):
        return getattr(obj, '_option_total', 0)


@admin.register(SurveyOption)
class SurveyOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'order', 'text', 'value')
    list_filter = ('question__campaign', 'question__question_type')
    search_fields = ('text', 'value', 'question__text', 'question__campaign__title')
    ordering = ('question', 'order', 'id')


@admin.register(SurveySubmission)
class SurveySubmissionAdmin(admin.ModelAdmin):
    inlines = [SurveyAnswerInline]
    list_display = ('id', 'campaign', 'user', 'answer_total', 'submitted_at')
    list_filter = ('campaign', 'submitted_at')
    search_fields = ('campaign__title', 'user__username', 'user__full_name')
    readonly_fields = ('campaign', 'user', 'submitted_at', 'created_at', 'updated_at')
    raw_id_fields = ('campaign', 'user')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_answer_total=Count('answers', distinct=True))

    @admin.display(description='Ответов', ordering='_answer_total')
    def answer_total(self, obj):
        return getattr(obj, '_answer_total', 0)

    def has_add_permission(self, request):
        return False


@admin.register(SurveyAnswer)
class SurveyAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'question', 'rating_value', 'selected_option', 'short_text_answer', 'selected_multiple')
    list_filter = ('question__campaign', 'question__question_type', 'submission__submitted_at')
    search_fields = ('question__text', 'submission__user__username', 'text_answer')
    raw_id_fields = ('submission', 'question', 'selected_option')

    @admin.display(description='Текст')
    def short_text_answer(self, obj):
        return (obj.text_answer or '')[:80] or '—'

    @admin.display(description='Multiple choice')
    def selected_multiple(self, obj):
        options = obj.selected_options.select_related('option').values_list('option__text', flat=True)
        return ', '.join(options) or '—'


@admin.register(SurveyAnswerOptionSelection)
class SurveyAnswerOptionSelectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'answer', 'option')
    list_filter = ('option__question__campaign',)
    raw_id_fields = ('answer', 'option')
