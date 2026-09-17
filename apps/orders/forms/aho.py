from django import forms

from apps.orders.choices import OrderAhoCategory
from apps.orders.models.aho import OrderAho


class BaseModalOrderAhoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = OrderAhoCategory

    class Meta:
        model = OrderAho
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


class ModalOrderAhoCreateForm(BaseModalOrderAhoForm):
    description = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 15}),
        required=True,
    )

    class Meta(BaseModalOrderAhoForm.Meta):
        pass


class ModalOrderAhoUpdateForm(BaseModalOrderAhoForm):
    class Meta(BaseModalOrderAhoForm.Meta):
        fields = [
            'status',
        ]
