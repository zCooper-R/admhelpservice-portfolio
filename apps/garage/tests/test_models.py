import logging

from django.core import mail
from django.test import TestCase

from apps.garage.models import Car, Service
from utils.mailer import Mailer

logger = logging.getLogger(__name__)


class EmailTest(TestCase):
    def test_send_email(self):
        mail.send_mail('Subject here', 'Here is the message.',
            'helpdesk@example.com', ['mechanic@example.com'],
            fail_silently=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Subject here')


class CarModelTest(TestCase):

    def __init__(self, methodName: str = ...):
        super().__init__(methodName)
        self.test_user1 = None

    @classmethod
    def setUpTestData(cls):

        test_car1 = Car.objects.create(
            brand='Ford',
            model='Focus',
            year='2023',
            state_number='A777AA',
            mileage=10_000,
            interval_oil_change=10_000,
            interval_timing_belt_change=80_000,
            interval_timing_roller_change=80_000,
        )

        test_car2 = Car.objects.create(
            brand='Toyota',
            model='Camry',
            year='2016',
            state_number='A345AA',
            mileage=10_000,
            interval_oil_change=11_000,
            interval_timing_belt_change=85_000,
            interval_timing_roller_change=85_000,
        )
        test_car3 = Car.objects.create(
            brand='Lada',
            model='Granta',
            year='2012',
            state_number='О123СA',
            mileage=10_000,
            interval_oil_change=9_000,
            interval_timing_belt_change=90_000,
            interval_timing_roller_change=90_000,
        )
        test_service_oil_car1 = Service.objects.create(
            car=test_car1,
            type_of_work=Service.TypeOfWork.OIL
        )
        test_service_oil_car2 = Service.objects.create(
            car=test_car2,
            type_of_work=Service.TypeOfWork.OIL
        )
        test_service_oil_car3 = Service.objects.create(
            car=test_car3,
            type_of_work=Service.TypeOfWork.OIL
        )

        test_service_timing_belt_car1 = Service.objects.create(
            car=test_car1,
            type_of_work=Service.TypeOfWork.TIMING_BELT
        )
        test_service_timing_belt_car2 = Service.objects.create(
            car=test_car2,
            type_of_work=Service.TypeOfWork.TIMING_BELT
        )
        test_service_timing_belt_car3 = Service.objects.create(
            car=test_car3,
            type_of_work=Service.TypeOfWork.TIMING_BELT
        )

        test_service_timing_roller_car1 = Service.objects.create(
            car=test_car1,
            type_of_work=Service.TypeOfWork.TIMING_ROLLER
        )
        test_service_timing_roller_car2 = Service.objects.create(
            car=test_car2,
            type_of_work=Service.TypeOfWork.TIMING_ROLLER
        )
        test_service_timing_roller_car3 = Service.objects.create(
            car=test_car3,
            type_of_work=Service.TypeOfWork.TIMING_ROLLER
        )

    def test_notify_oil_change_due(self):
        car1 = Car.objects.get(id=1)
        car2 = Car.objects.get(id=2)
        car3 = Car.objects.get(id=3)

        car1.update_mileage(20_000)
        self.assertTrue(car1.is_oil_change_due())

        car2.update_mileage(20_499)
        self.assertFalse(car2.is_oil_change_due())

        car3.update_mileage(20_501)
        self.assertTrue(car3.is_oil_change_due())

    def test_notify_timing_belt_change_due(self):
        car1 = Car.objects.get(id=1)
        car2 = Car.objects.get(id=2)
        car3 = Car.objects.get(id=3)

        car1.update_mileage(90_000)
        self.assertTrue(car1.is_timing_belt_change_due())

        car2.update_mileage(94_499)
        self.assertFalse(car2.is_timing_belt_change_due())

        car3.update_mileage(100_501)
        self.assertTrue(car3.is_timing_belt_change_due())

    def test_notify_timing_roller_change_due(self):
        car1 = Car.objects.get(id=1)
        car2 = Car.objects.get(id=2)
        car3 = Car.objects.get(id=3)

        car1.update_mileage(90_000)
        self.assertTrue(car1.is_timing_roller_change_due())

        car2.update_mileage(94_499)
        self.assertFalse(car2.is_timing_roller_change_due())

        car3.update_mileage(100_501)
        self.assertTrue(car3.is_timing_roller_change_due())
