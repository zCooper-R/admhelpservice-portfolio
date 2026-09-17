from django import template
from django.db.models import IntegerChoices

register = template.Library()


@register.inclusion_tag('orders/include/form_create_popover_help.html')
def render_category_descriptions_popover(bound_field):
    """
    Получает enum_class, если он был установлен в форме.
    """
    enum_class = getattr(bound_field.form, "enum_class", None)
    if not enum_class or not issubclass(enum_class, IntegerChoices):
        return {"descriptions": []}

    field_choices = {
        value for value, _label in bound_field.field.choices
        if value not in ('', None)
    }

    return {
        "descriptions": [
            {
                "label": choice.label,
                "value": choice.value,
                "description": enum_class.get_description(choice.value)
            } for choice in enum_class
            if choice.value in field_choices
        ]
    }


@register.filter
def split_transport_route(value):
    if not value:
        return []

    return [point.strip() for point in str(value).split(' -> ') if point.strip()]
