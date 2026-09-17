from django.conf import settings
from django.db import models

from apps.orders.models.mixins import TimeStampMixin


class Feedback(TimeStampMixin):
    """
    Модель обратной связи
    """

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='От кого',
        related_name='feedbacks',
        on_delete=models.SET_NULL,
        null=True
    )
    message = models.TextField(verbose_name="Текст обращения")
    email = models.EmailField(verbose_name="Куда ответить", blank=True, null=True)

    class Meta:
        verbose_name = "Обратная связь"
        verbose_name_plural = "Обратная связь"

    def __str__(self):
        return str(self.from_user)
