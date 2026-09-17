from django import forms

from apps.orders.models.feedback import Feedback


class HelpForm(forms.ModelForm):
    class Meta:
        model = Feedback

        fields = [
            'email',
            'message',
        ]
        labels = {
            'message': 'Введите текст обращения',
            'email': 'Ваш email адрес',
        }

        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': ' '}),
            'message': forms.Textarea(attrs={'style': 'height:150px', 'placeholder': ' '}),

        }
