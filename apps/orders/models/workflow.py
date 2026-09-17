from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.users.models import SupportSpecialist, TechnicalGroup


class OrderWorkflowRule(models.Model):
    class AssignmentStrategy(models.TextChoices):
        ROUND_ROBIN = "round_robin", "По очереди"

    content_type = models.OneToOneField(
        ContentType,
        on_delete=models.CASCADE,
        related_name="order_workflow_rule",
        verbose_name="Тип заявки",
    )
    technical_group = models.ForeignKey(
        TechnicalGroup,
        on_delete=models.SET_NULL,
        related_name="order_workflow_rules",
        null=True,
        blank=True,
        verbose_name="Техническая группа",
        help_text="Не влияет на выбор исполнителя. Используется как организационный контекст и фильтр.",
    )
    moderator_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="order_workflow_rules",
        verbose_name="Группы модераторов",
    )
    eligible_specialists = models.ManyToManyField(
        SupportSpecialist,
        blank=True,
        related_name="order_workflow_rules",
        verbose_name="Доступные исполнители",
    )
    auto_assign_enabled = models.BooleanField(default=True, verbose_name="Автоназначение включено")
    assignment_strategy = models.CharField(
        max_length=32,
        choices=AssignmentStrategy.choices,
        default=AssignmentStrategy.ROUND_ROBIN,
        verbose_name="Стратегия назначения",
    )
    last_assigned_specialist = models.ForeignKey(
        SupportSpecialist,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Последний назначенный исполнитель",
    )

    class Meta:
        verbose_name = "Правило маршрутизации заявок"
        verbose_name_plural = "Правила маршрутизации заявок"
        ordering = ["content_type__app_label", "content_type__model"]

    def __str__(self) -> str:
        return f"{self.content_type.app_label}.{self.content_type.model}"

    @property
    def category_label(self) -> str:
        model_class = self.content_type.model_class()
        if model_class is None:
            return self.content_type.model
        return str(model_class._meta.verbose_name)
