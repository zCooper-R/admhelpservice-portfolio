from django import forms

from apps.orders.choices import OrderAccountCategory
from apps.orders.models.account import OrderAccount


class BaseModalOrderAccountForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = OrderAccountCategory

        category_field = self.fields.get('category')
        if category_field is not None:
            category_field.choices = [
                choice for choice in category_field.choices
                if choice[0] != OrderAccountCategory.CREATE
            ]

    class Meta:
        model = OrderAccount
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


class ModalOrderAccountCreateForm(BaseModalOrderAccountForm):
    description = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 15}),
        required=True,
    )


class ModalOrderAccountUpdateForm(BaseModalOrderAccountForm):
    class Meta(BaseModalOrderAccountForm.Meta):
        fields = [
            'status',
        ]
