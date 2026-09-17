from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


@register.simple_tag
def get_verbose_field_name(instance, field_name):
    """
    Returns verbose_name for a field.
    """
    return instance._meta.get_field(field_name).verbose_name.title()


@register.filter
def content_type(obj):
    """
    Возвращает объект content_type для obj

    Использование:
        {% with order| content_type as ctype %}
        <td>{{ ctype.pk }}</td>
        {% endwith %}
    """
    if not obj:
        return False
    ct = ContentType.objects.get_for_model(obj)
    return ct


@register.filter
def date_no_tz(obj):
    return obj.localize()
