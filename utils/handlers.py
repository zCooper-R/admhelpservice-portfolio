import json
from pprint import pprint

import django.forms


class FieldHandler:
    formfields = {}

    def __init__(self, fields):
        for field in fields:
            options = self.get_options(field)
            f = getattr(self, "create_field_for_"+field['type'] )(field, options)
            self.formfields[field['name']] = f

    def get_options(self, field):
        options = {
            'label': field['label'],
            'help_text': field.get("help_text", None),
            'required': bool(field.get("required", 0))
        }
        return options

    def create_field_for_text(self, field, options):
        options['max_length'] = int(field.get("max_length", "20"))
        return django.forms.CharField(**options)

    def create_field_for_textarea(self, field, options):
        options['max_length'] = int(field.get("max_value", "9999"))
        return django.forms.CharField(widget=django.forms.Textarea, **options)

    def create_field_for_integer(self, field, options):
        options['max_value'] = int(field.get("max_value", "999999999"))
        options['min_value'] = int(field.get("min_value", "-999999999"))
        return django.forms.IntegerField(**options)

    def create_field_for_radio(self, field, options):
        options['choices'] = [(c['value'], c['name'] ) for c in field['choices']]
        return django.forms.ChoiceField(widget=django.forms.RadioSelect,   **options)

    def create_field_for_select(self, field, options):
        options['choices'] = [(c['value'], c['name'] ) for c in field['choices']]
        return django.forms.ChoiceField(**options)

    def create_field_for_checkbox(self, field, options):
        return django.forms.BooleanField(widget=django.forms.CheckboxInput, **options)


json_fields = """[
        {
            "name": "firstname",
            "label": "First Name",
            "type": "text",
            "max_length": 25,
            "required": 1
        },
        {
            "name": "lastname",
            "label": "Last Name",
            "type": "text",
            "max_length": 25,
            "required": 1
        },
        {
            "name": "smallcv",
            "label": "Small CV",
            "type": "textarea",
            "help_text": "Please insert a small CV"
        },
        {
            "name": "age",
            "label": "Age",
            "type": "integer",
            "max_value": 200,
            "min_value": 0
        },
        {
            "name": "marital_status",
            "label": "Marital Status",
            "type": "radio",
            "choices": [
                {"name": "Single", "value":"single"},
                {"name": "Married", "value":"married"},
                {"name": "Divorced", "value":"divorced"},
                {"name": "Widower", "value":"widower"}
            ]
        },
        {
            "name": "occupation",
            "label": "Occupation",
            "type": "select",
            "choices": [
                {"name": "Farmer", "value":"farmer"},
                {"name": "Engineer", "value":"engineer"},
                {"name": "Teacher", "value":"teacher"},
                {"name": "Office Clerk", "value":"office_clerk"},
                {"name": "Merchant", "value":"merchant"},
                {"name": "Unemployed", "value":"unemployed"},
                {"name": "Retired", "value":"retired"},
                {"name": "Other", "value":"other"}
            ]
        },
        {
            "name": "internet",
            "label": "Internet Access",
            "type": "checkbox"
        }
    ]
    """


def get_form(jstr):
    _fields = json.loads(jstr)
    fh = FieldHandler(_fields)
    return type('DynaForm', (django.forms.Form,), fh.formfields )


if __name__ == '__main__':
    a = get_form(json_fields)
    import logging

    logging.getLogger(__name__).info('dynamic form generated form_class=%s', a.__name__)
