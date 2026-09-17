from django import forms

from apps.orders.models.transport import OrderTransport


class BaseModalTransportForm(forms.ModelForm):
    class Meta:
        abstract = True
        model = OrderTransport
        fields = [
            'client',
            'departament',
            'phone',
            'transport_city',
            'address',
            'description',
            'transport_arrival_datetime',
            'transport_departure_datetime',
            'transport_passengers',
            'transport_departure_location',
            'comeback',
            'comeback_datetime',
            'driver',
            'status',
        ]
        labels = {
            'transport_city': 'Город/район',
            'transport_arrival_datetime': 'Дата и время прибытия',
            'transport_departure_datetime': 'Дата и время отправления',
            'transport_departure_location': 'Место отправления',
            'driver': 'Водитель',
            'status': 'Статус',
            'address': 'Куда?',
            'description': 'Комментарий',
            'phone': 'Контактный тел.',
            'transport_passengers': 'Кол-во человек',
            'comeback': 'Поедете обратно?',
        }
        widgets = {
            'transport_departure_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'transport_arrival_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 15}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'category': '<- Описание подкатегорий',
        }


class ModalOrderTransportCreateForm(BaseModalTransportForm):
    class Meta(BaseModalTransportForm.Meta):
        exclude = [
            'comeback_datetime',
            'driver',
            'status',
        ]


class ModalOrderTransportUpdateForm(BaseModalTransportForm):
    class Meta(BaseModalTransportForm.Meta):
        exclude = [
            'comeback',
        ]


BaseModalTransportForm.Meta.labels.update({
    'address': 'Маршрут',
})

BaseModalTransportForm.Meta.widgets.update({
    'description': forms.Textarea(attrs={'rows': 2, 'cols': 15}),
})


class OrderTransportUpdateForm(BaseModalTransportForm):
    class Meta:
        model = OrderTransport
        fields = [
            'client',
            'departament',
            'phone',
            'address',
            'description',
            'transport_departure_datetime',
            'transport_departure_location',
            'driver',
            'status',
        ]
        widgets = {
            'transport_departure_datetime': forms.TextInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'transport_departure_datetime': 'Время отправления',
            'transport_departure_location': 'Место отправления',
            'driver': 'Водитель',
            'status': 'Статус',
        }
        help_texts = {
            'address': 'Добавьте несколько адресов, если необходимо',
        }
