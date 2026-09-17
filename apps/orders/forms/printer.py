from django import forms

from apps.orders.choices import OrderPrinterCategory
from apps.orders.models.printer import OrderPrinter


class BaseModalPrinterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = OrderPrinterCategory

    class Meta:
        abstract = True
        model = OrderPrinter
        fields = [
            'status',
            'category',
            'printer_name',
            'departament',
            'client',
            'address',
            'cabinet',
            'phone',
            'description',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 15}),
        }
        labels = {
            'description': 'Комментарий',
            'printer_name': 'Имя принтера (см. наклейка на принтере)',
            'address': 'Адрес',
            'phone': 'Контактный тел.',
        }
        help_texts = {
            'category': '<- Описание подкатегорий',
            'printer_name': 'пример: Canon MF267dw, 16-2, сеть 80',
        }


class ModalOrderPrinterCreateForm(BaseModalPrinterForm):
    class Meta(BaseModalPrinterForm.Meta):
        exclude = [
            'status',
        ]

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        description = (cleaned_data.get('description') or '').strip()

        if category != OrderPrinterCategory.REFILL and not description:
            self.add_error('description', 'Пожалуйста, введите описание.')

        return cleaned_data


class ModalOrderPrinterUpdateForm(BaseModalPrinterForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
