from django import forms

from apps.orders.choices import OrderVKSCategory, OrderVKSEquipment
from apps.orders.models.vks import OrderVKS


class ModalOrderVKSCreateForm(forms.ModelForm):
    equipment = forms.MultipleChoiceField(
        label='Что должно работать во время подключения',
        choices=OrderVKSEquipment.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = OrderVKS
        fields = [
            'departament',
            'client',
            'phone',
            'cabinet',
            'address',
            'description',
            'category',
            'equipment',
            'name_vks',
            'start_vks_datetime',
            'duration_vks_time',
            'link_vks',
            'recipient_email',
        ]
        labels = {
            'phone': 'Контактный тел.',
            'address': 'Где будет проходить встреча',
            'cabinet': 'Кабинет / помещение',
            'description': 'Комментарий',
        }
        help_texts = {
            'category': '<- Описание подкатегорий',
            'link_vks': 'Вставьте полную ссылку для подключения, если она уже есть.',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 15, 'placeholder': 'Дополнительные детали, пожелания или важные организационные нюансы.'}),
            'name_vks': forms.TextInput(attrs={'placeholder': 'Например: Планёрка отдела цифровизации'}),
            'recipient_email': forms.EmailInput(attrs={'placeholder': 'name@example.com'}),
            'link_vks': forms.TextInput(attrs={'placeholder': 'https://telemost.yandex.ru/...'}),
            'start_vks_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'duration_vks_time': forms.NumberInput(attrs={'step': '0.5', 'min': '0.5', 'placeholder': '1.0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = OrderVKSCategory

        if self.instance and self.instance.pk and self.instance.equipment:
            self.initial['equipment'] = [
                item.strip() for item in str(self.instance.equipment).split(',') if item.strip()
            ]

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        equipment = cleaned_data.get('equipment') or []

        if category == OrderVKSCategory.ORGANIZE:
            self._require('name_vks', 'Укажите название трансляции.')
            self._require('start_vks_datetime', 'Укажите дату и время проведения.')
            self._require('duration_vks_time', 'Укажите длительность встречи.')
            self._require('recipient_email', 'Укажите, куда отправить ссылку на трансляцию.')

            cleaned_data['link_vks'] = ''
            cleaned_data['equipment'] = ''

        elif category == OrderVKSCategory.CONNECT:
            self._require('address', 'Укажите, где будет проходить подключение.')
            self._require('cabinet', 'Укажите кабинет или помещение.')
            self._require('start_vks_datetime', 'Укажите дату и время подключения.')
            self._require('link_vks', 'Укажите ссылку для подключения.')
            if not equipment:
                self.add_error('equipment', 'Выберите, что должно работать во время подключения.')

            cleaned_data['recipient_email'] = ''
            cleaned_data['name_vks'] = ''
            cleaned_data['duration_vks_time'] = None

        elif category == OrderVKSCategory.PRESENTATION:
            self._require('address', 'Укажите, где будет проходить презентация.')
            self._require('cabinet', 'Укажите кабинет или помещение.')
            self._require('start_vks_datetime', 'Укажите дату и время презентации.')

            cleaned_data['link_vks'] = ''
            cleaned_data['recipient_email'] = ''
            cleaned_data['name_vks'] = ''
            cleaned_data['duration_vks_time'] = None

        return cleaned_data

    def _require(self, field_name, message):
        value = self.cleaned_data.get(field_name)
        if value in (None, '', []):
            self.add_error(field_name, message)

    def clean_equipment(self):
        values = self.cleaned_data.get('equipment') or []
        return ','.join(values)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.category == OrderVKSCategory.ORGANIZE and instance.name_vks:
            instance.title = f'Трансляция: {instance.name_vks}'[:100]
        elif instance.category == OrderVKSCategory.CONNECT:
            place = instance.cabinet or instance.address
            instance.title = f'Подключение к ВКС: {place}'[:100]
        elif instance.category == OrderVKSCategory.PRESENTATION:
            place = instance.cabinet or instance.address
            instance.title = f'Презентация: {place}'[:100]

        if commit:
            instance.save()
        return instance


class ModalOrderVksUpdateForm(forms.ModelForm):
    class Meta:
        model = OrderVKS
        fields = [
            'status',
        ]
