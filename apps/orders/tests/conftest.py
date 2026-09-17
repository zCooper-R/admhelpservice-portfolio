import pytest
from django.db import models
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.orders.models.base import BaseOrder

@pytest.fixture
def request_with_user(db):
    user_model = get_user_model()
    user = user_model.objects.create_user(username="testuser", password="123")
    request = RequestFactory().get('/')
    request.user = user
    return request

@pytest.fixture
def dummy_model_class():
    class DummyOrderModel(BaseOrder):
        class Meta:
            app_label = "orders"
            managed = True
            db_table = "orders_dummyordermodel"

    if not apps.get_model("orders", "DummyOrderModel"):
        apps.register_model("orders", DummyOrderModel)

    return DummyOrderModel


@pytest.fixture
def dummy_model_instance(dummy_model_class):
    return dummy_model_class.objects.create(
        client="Тест Клиент",
        address="Тест адрес",
        phone="123-456"
    )


@pytest.fixture
def dummy_form(dummy_model_instance):
    class DummyForm:
        def __init__(self, instance):
            self.instance = instance

        def save(self):
            return self.instance

    return DummyForm(instance=dummy_model_instance)
