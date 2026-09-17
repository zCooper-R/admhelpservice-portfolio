import logging

from django.conf import settings

from apps.garage.gpsApi import GpsApi
from apps.garage.models import Car
from apps.users.models import User
from utils.mailer import Mailer
from utils.tlg_sender import TelegramSender


logger = logging.getLogger('adm.apps.garage')
audit_logger = logging.getLogger('adm.audit')

TRACKER_TYPE_ODOMETER = 'odometer'
TRACKER_TYPE_ENGINE_HOURS = 'engine_hours'


def get_all_tracker_ids() -> list:
    return list(Car.objects.filter(tracker_id__isnull=False).values_list('tracker_id', flat=True).distinct())


def update_car_mileage_and_engine_hours():
    logger.info('garage mileage sync started', extra={'event': 'garage_mileage_sync_started'})
    try:
        gps_api = GpsApi(login=settings.GPS_AUVTOCONTROL_LOGIN, password=settings.GPS_AUVTOCONTROL_PASSWORD)
        tracker_ids = get_all_tracker_ids()
        odometer_counters = gps_api.get_trackers_counter_values(tracker_ids, TRACKER_TYPE_ODOMETER)
        engine_hours_counters = gps_api.get_trackers_counter_values(tracker_ids, TRACKER_TYPE_ENGINE_HOURS)

        updated_count = 0
        for car in Car.objects.exclude(tracker_id__isnull=True):
            tracker_id = str(car.tracker_id)
            if tracker_id in odometer_counters and tracker_id in engine_hours_counters:
                car.update_mileage(odometer_counters[tracker_id])
                car.update_engine_hours(engine_hours_counters[tracker_id])
                car.save(update_fields=['mileage', 'engine_hours', 'updated_at'])
                updated_count += 1
        logger.info('garage mileage sync finished updated_cars=%s', updated_count, extra={'event': 'garage_mileage_sync_finished'})
    except Exception:
        logger.exception('garage mileage sync failed')
        raise


def notify_mechanic(template=None):
    if template is None:
        template = 'garage/email/car_email_notify_mechanic.html'

    mailer = Mailer()
    telegramer = TelegramSender()

    users = User.objects.filter(groups__name='adm_moderator_mehanik')
    emails_to = [user.email for user in users if user.email]
    tlgs_to = [user.tlg_id for user in users if user.tlg_id]

    notifications_sent = 0
    for car in Car.objects.all():
        if car.is_oil_change_due():
            _notify_mechanic_about_car(
                car=car,
                mailer=mailer,
                telegramer=telegramer,
                emails_to=emails_to,
                tlgs_to=tlgs_to,
                subject=f'Для {car} необходима замена масла!',
                template=template,
                message=f'Для {car} необходима замена масла!',
                event='garage_oil_due',
            )
            notifications_sent += 1

        if car.is_timing_belt_change_due():
            _notify_mechanic_about_car(
                car=car,
                mailer=mailer,
                telegramer=telegramer,
                emails_to=emails_to,
                tlgs_to=tlgs_to,
                subject=f'Для {car} необходима замена ремня ГРМ!',
                template=template,
                message=f'Для {car} необходима замена ремня ГРМ!',
                event='garage_timing_belt_due',
            )
            notifications_sent += 1

        if car.is_timing_roller_change_due():
            _notify_mechanic_about_car(
                car=car,
                mailer=mailer,
                telegramer=telegramer,
                emails_to=emails_to,
                tlgs_to=tlgs_to,
                subject=f'Для {car} необходима замена роликов ГРМ!',
                template=template,
                message=f'Для {car} необходима замена роликов ГРМ!',
                event='garage_timing_roller_due',
            )
            notifications_sent += 1

    logger.info('garage mechanic notifications finished sent=%s', notifications_sent, extra={'event': 'garage_notifications_finished'})


def _notify_mechanic_about_car(*, car, mailer, telegramer, emails_to, tlgs_to, subject, template, message, event):
    logger.warning('%s car_id=%s tracker_id=%s', event, car.id, car.tracker_id, extra={'event': event})
    mailer.send_messages(
        subject=subject,
        template=template,
        context={'object': car},
        to_emails=emails_to,
    )
    telegramer.send_messages(tlg_ids=tlgs_to, message=message)
    audit_logger.info(
        'garage notification sent action=%s car_id=%s state_number=%s',
        event,
        car.id,
        car.state_number,
        extra={'event': 'audit'},
    )
