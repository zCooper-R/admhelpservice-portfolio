"""
Celery-задачи приложения orders. Реализация в mail.py / telegram.py.
Импорты ниже нужны для autodiscover_tasks и обратной совместимости:
    from apps.orders.tasks import task_mail_admins
"""
from apps.orders.tasks.mail import (
    task_mail_admins,
    task_mail_admins_feedback,
    task_mail_organisation,
    task_mail_organisation_from_admin_panel,
    task_mail_protection_sector,
    task_process_done_order_printer_fill_emails,
)
from apps.orders.tasks.sla import task_process_sla_reminders
from apps.orders.tasks.telegram import (
    task_notification_user,
    task_notify_specialist,
    task_send_order_object_telegram,
    task_telegram_account_moderators,
    task_telegram_aho_moderators,
    task_telegram_pc_moderators,
    task_telegram_printer_moderators,
    task_telegram_transport_moderators,
)

__all__ = [
    'task_mail_admins',
    'task_mail_admins_feedback',
    'task_mail_organisation',
    'task_mail_organisation_from_admin_panel',
    'task_mail_protection_sector',
    'task_process_done_order_printer_fill_emails',
    'task_process_sla_reminders',
    'task_notification_user',
    'task_notify_specialist',
    'task_send_order_object_telegram',
    'task_telegram_account_moderators',
    'task_telegram_aho_moderators',
    'task_telegram_pc_moderators',
    'task_telegram_printer_moderators',
    'task_telegram_transport_moderators',
]
