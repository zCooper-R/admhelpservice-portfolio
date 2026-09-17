import logging

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.forms import model_to_dict
from django.urls import reverse

logger = logging.getLogger('adm.apps.orders')

class TimeStampMixin(models.Model):
    """
    Абстрактная модель. Добавляет к модели
    дату создания и дату изменения.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')

    class Meta:
        abstract = True


class OrderWrapperMixin(models.Model):
    """
    Миксин для автоматического создания "обертки" Order
    при создании любой конкретной заявки.
    """
    class Meta:
        abstract = True

    @transaction.atomic # Гарантирует, что обе операции (сохранение заявки и обертки) выполнятся успешно
    def save(self, *args, **kwargs):
        # Сначала сохраняем основной объект (например, OrderTransport)
        super().save(*args, **kwargs)

        from apps.orders.models.base import Order
        # Теперь создаем для него обертку Order, если ее еще нет
        # Мы используем update_or_create, чтобы избежать дубликатов при повторном сохранении
        Order.objects.update_or_create(
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
            defaults={'owner': self.owner}
        )


class ChoicesDisplayMixin:
    def to_dict(self) -> dict:
        data = model_to_dict(self)
        for field in self._meta.fields:
            if field.choices:
                # Автоматически вызываем get_XXX_display для каждого поля с choices
                display_method = getattr(self, f'get_{field.name}_display', None)
                if display_method:
                    data[field.name] = display_method()
        return data


class OrderCategoryMixin(models.Model):
    class Meta:
        abstract = True

    def get_context(self) -> dict:
        return {
            'owner': self.owner,
            'client': self.client,
            'address': self.address,
            'description': self.description,
            'phone': self.phone,
            'cabinet': self.cabinet,
            'category': self.get_category_display()
        }

    def __str__(self):
        return f'{self.__class__.__name__}-{self.get_category_display()}'

    def user_can_view_me(self, user):
        return user == self.owner or user.has_perm(f'orders.view_{self._meta.model_name}')

    def get_absolute_url(self):
        return reverse(f'orders:{self._meta.model_name}_detail', kwargs={'pk': self.pk})

    def get_category_display_name(self):
        return f"{self._meta.verbose_name}-{self.get_category_display()}"

    @staticmethod
    def get_template_mail_admin(**kwargs) -> str:
        return f'orders/email/admin/{self._meta.model_name}_email_to_admin.html'


class TrackChangesModel(models.Model):
    class Meta:
        abstract = True

    def _get_original_instance(self):
        qs = self.__class__.objects
        try:
            select_fields = ['owner', 'support_specialist']
            qs = qs.select_related(*[f for f in select_fields if hasattr(self, f)])
        except Exception:
            logger.exception('order change tracking select_related preparation failed model=%s pk=%s', self.__class__.__name__, self.pk)
        return qs.filter(pk=self.pk).first()

    def track_changes(self, exclude_fields=None):
        changed_fields = {}
        exclude_fields = exclude_fields or []

        orig_instance = self._get_original_instance()
        if not orig_instance:
            return changed_fields

        for field in self._meta.fields:
            field_name = field.name
            if field_name in exclude_fields:
                continue
            orig_value = getattr(orig_instance, field_name)
            curr_value = getattr(self, field_name)
            if orig_value != curr_value:
                changed_fields[field_name] = (orig_value, curr_value)

        return changed_fields
