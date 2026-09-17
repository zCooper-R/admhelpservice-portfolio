
from django.test import TestCase
from django.urls import reverse



# class TransportTestCase(TestCase):
# 	"""
# 	Тестируем Регистрацию Автомобилей
# 	"""
# 	def setUp(self):
# 		self.driver = Driver.objects.create(name='User',
# 		                                    phone='+38096000000',
# 		                                    transport_id=1)
# 		Transport.objects.create(
# 			id=1,
# 			state_number='AA1111BB',
# 			brand='BMW',
# 			model='X6',
# 			driver=self.driver)
#
# 	def test_get_driver_link(self):
# 		"""
# 		Проверяем правильно ли создаётся ссылка на водителя
# 		"""
# 		transport = Transport.objects.get(state_number='AA1111BB')
# 		driver_link = transport.driver_link()
# 		self.assertEqual(
# 			driver_link,
# 			reverse('admin:orders_driver_change',
# 			        args=(self.driver.pk,)))
