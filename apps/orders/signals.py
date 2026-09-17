from django.conf import settings

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.orders.models.printer import OrderPrinter
from apps.orders.models.pc import OrderPC
from apps.orders.models.account import OrderAccount



# @receiver(post_save, sender=OrderPrinter)
# def notify_orderprinter_telegram_technical_group_L1(sender, instance, created, **kwargs):
#     if created:
#         if not settings.DEBUG:
#             if isinstance(instance, OrderPrinter):
#                 if instance.is_refill_category():
#                     return
#             task_notify_specialist.delay(object_id=instance.id, content_type_model='orderprinter')
#
#
# @receiver(post_save, sender=OrderPC)
# def notify_orderpc_telegram_technical_group_L1(sender, instance, created, **kwargs):
#     if created:
#         if not settings.DEBUG:
#             task_notify_specialist.delay(object_id=instance.id, content_type_model='orderpc')
#
#
# @receiver(post_save, sender=OrderAccount)
# def notify_orderaccount_telegram_technical_group_L1(sender, instance, created, **kwargs):
#     if created:
#         if not settings.DEBUG:
#             task_notify_specialist.delay(object_id=instance.id, content_type_model='orderaccount')
#
