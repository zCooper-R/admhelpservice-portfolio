from django import template
register = template.Library()


@register.filter
def is_visible(field):
    return hasattr(field, 'field') and field.field.widget.is_hidden is False
