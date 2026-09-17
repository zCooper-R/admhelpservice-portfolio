from apps.orders.choices import OrderAccountCategory, OrderPrinterCategory, OrderVKSCategory
from apps.orders.forms.account import ModalOrderAccountCreateForm
from apps.orders.forms.aho import ModalOrderAhoCreateForm
from apps.orders.forms.pc import ModalOrderPcCreateForm
from apps.orders.forms.printer import ModalOrderPrinterCreateForm
from apps.orders.forms.transport import ModalOrderTransportCreateForm
from apps.orders.forms.vks import ModalOrderVKSCreateForm
from apps.orders.templatetags.order_tags import render_category_descriptions_popover, split_transport_route


def test_account_create_form_hides_create_category():
    form = ModalOrderAccountCreateForm()

    category_values = {value for value, _label in form.fields['category'].choices if value != ''}

    assert OrderAccountCategory.CREATE not in category_values


def test_account_create_form_requires_description():
    form = ModalOrderAccountCreateForm(data={
        'category': OrderAccountCategory.DISABLE,
        'departament': 'IT',
        'client': 'Test User',
        'phone': '12345',
        'cabinet': '101',
        'address': 'Main office',
        'description': '',
    })

    assert not form.is_valid()
    assert 'description' in form.errors


def test_account_category_popover_shows_only_available_choices():
    form = ModalOrderAccountCreateForm()

    descriptions = render_category_descriptions_popover(form['category'])['descriptions']
    description_values = {item['value'] for item in descriptions}

    assert OrderAccountCategory.CREATE not in description_values


def test_required_description_for_account_aho_pc():
    forms = [
        ModalOrderAccountCreateForm(),
        ModalOrderAhoCreateForm(),
        ModalOrderPcCreateForm(),
    ]

    for form in forms:
        assert form.fields['description'].required is True


def test_optional_description_for_printer_transport_and_vks():
    forms = [
        ModalOrderPrinterCreateForm(),
        ModalOrderTransportCreateForm(),
        ModalOrderVKSCreateForm(),
    ]

    for form in forms:
        assert form.fields['description'].required is False


def test_printer_description_not_required_for_refill():
    form = ModalOrderPrinterCreateForm(data={
        'category': OrderPrinterCategory.REFILL,
        'printer_name': 'Canon MF267dw',
        'departament': 'IT',
        'client': 'Test User',
        'address': 'Office',
        'cabinet': '101',
        'phone': '12345',
        'description': '',
    })

    assert form.is_valid()


def test_printer_description_required_for_non_refill():
    form = ModalOrderPrinterCreateForm(data={
        'category': OrderPrinterCategory.REPAIR,
        'printer_name': 'Canon MF267dw',
        'departament': 'IT',
        'client': 'Test User',
        'address': 'Office',
        'cabinet': '101',
        'phone': '12345',
        'description': '',
    })

    assert not form.is_valid()
    assert 'description' in form.errors


def test_split_transport_route_filter():
    route = 'Арзамас, ул. Ленина, 1 -> Кремль -> ул. Калинина, 40'

    assert split_transport_route(route) == [
        'Арзамас, ул. Ленина, 1',
        'Кремль',
        'ул. Калинина, 40',
    ]


def test_vks_organize_requires_broadcast_fields():
    form = ModalOrderVKSCreateForm(data={
        'category': OrderVKSCategory.ORGANIZE,
        'departament': 'IT',
        'client': 'Test User',
        'phone': '12345',
        'cabinet': '101',
        'address': 'Main office',
        'description': '',
        'name_vks': '',
        'start_vks_datetime': '',
        'duration_vks_time': '',
        'recipient_email': '',
        'link_vks': '',
    })

    assert not form.is_valid()
    assert 'name_vks' in form.errors
    assert 'start_vks_datetime' in form.errors
    assert 'duration_vks_time' in form.errors
    assert 'recipient_email' in form.errors


def test_vks_connect_requires_link_time_and_equipment():
    form = ModalOrderVKSCreateForm(data={
        'category': OrderVKSCategory.CONNECT,
        'departament': 'IT',
        'client': 'Test User',
        'phone': '12345',
        'cabinet': '101',
        'address': 'Main office',
        'description': '',
        'name_vks': '',
        'start_vks_datetime': '',
        'duration_vks_time': '',
        'recipient_email': '',
        'link_vks': '',
    })

    assert not form.is_valid()
    assert 'start_vks_datetime' in form.errors
    assert 'link_vks' in form.errors
    assert 'equipment' in form.errors


def test_vks_presentation_requires_time_and_place_but_not_equipment_or_link():
    form = ModalOrderVKSCreateForm(data={
        'category': OrderVKSCategory.PRESENTATION,
        'departament': 'IT',
        'client': 'Test User',
        'phone': '12345',
        'cabinet': '',
        'address': '',
        'description': '',
        'name_vks': '',
        'start_vks_datetime': '',
        'duration_vks_time': '',
        'recipient_email': '',
        'link_vks': '',
    })

    assert not form.is_valid()
    assert 'address' in form.errors
    assert 'cabinet' in form.errors
    assert 'start_vks_datetime' in form.errors
    assert 'equipment' not in form.errors
    assert 'link_vks' not in form.errors
