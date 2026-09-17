# from django.test import TestCase
# from django.urls import reverse
#
# from Fills.models import Fill
# from Users.models import User
#
#
# class FillListViewTest(TestCase):
#
#     @classmethod
#     def setUpTestData(cls):
#         user = User.objects.create(username='testFillView')
#         user.set_password('1X<ISRUkw+tuK')
#         user.save()
#         number_of_fills = 19
#
#         for fill_id in range(number_of_fills):
#             Fill.objects.create(user=user,
#                                 client=f'testUser{fill_id}',
#                                 title=f'Ремонт{fill_id}',
#                                 description=f'Почините принтер{fill_id}',
#                                 address=f'ул. Примерная, 10-{fill_id}',
#                                 cabinet=f'25-{fill_id}',
#                                 phone=f'7-58-59-{fill_id}')
#
#     def test_view_url_exists_at_desired_location(self):
#         login = self.client.login(username='testFillView', password='test-password')
#         self.assertTrue(login)
#         response = self.client.get('/fills/')
#         self.assertEqual(response.status_code, 200)
#
#     def test_view_url_accessible_by_name(self):
#         login = self.client.login(username='testFillView', password='test-password')
#         self.assertTrue(login)
#         response = self.client.get(reverse('fills:fills_list'))
#         self.assertEqual(response.status_code, 200)
#
#     def test_view_uses_correct_template(self):
#         login = self.client.login(username='testFillView', password='test-password')
#         self.assertTrue(login)
#         response = self.client.get(reverse('fills:fills_list'))
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'fills/fills_list.html')
#
#     def test_pagination_is_sixteen(self):
#         """Get first page and confirm it have (exactly) 16 fills"""
#         login = self.client.login(username='testFillView', password='test-password')
#         self.assertTrue(login)
#         response = self.client.get(reverse('fills:fills_list'))
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('is_paginated' in response.context)
#         self.assertTrue(response.context['is_paginated'])
#         self.assertEqual(len(response.context['fills']), 16)
#
#     def test_lists_all_other_fills(self):
#         """Get second page and confirm it has (exactly) remaining 3 fills"""
#         login = self.client.login(username='testFillView', password='test-password')
#         self.assertTrue(login)
#         response = self.client.get(reverse('fills:fills_list') + '?page=2')
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('is_paginated' in response.context)
#         self.assertTrue(response.context['is_paginated'])
#         self.assertEqual(len(response.context['fills']), 3)
