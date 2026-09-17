from django import forms

from apps.orders.choices import OrderPcCategory
from apps.orders.models.pc import OrderPC


class BaseModalOrderPcForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = OrderPcCategory

    class Meta:
        model = OrderPC
        fields = [
            'category',
            'departament',
            'client',
            'phone',
            'cabinet',
            'address',
            'description',
        ]
        labels = {
            'description': 'Комментарий',
            'phone': 'Контактный тел.',
        }
        help_texts = {
            'category': '<- Описание подкатегорий',
        }


class ModalOrderPcCreateForm(BaseModalOrderPcForm):
    description = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 15}),
        required=True,
    )

    class Meta(BaseModalOrderPcForm.Meta):
        pass


class ModalOrderPcUpdateForm(BaseModalOrderPcForm):
    class Meta(BaseModalOrderPcForm.Meta):
        fields = [
            'status',
        ]
