import logging

from django.db import models
from django.utils import timezone


logger = logging.getLogger('adm.apps.garage')


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')

    class Meta:
        abstract = True


class Car(TimestampMixin):
    brand = models.CharField(verbose_name='Марка', max_length=255)
    model = models.CharField(verbose_name='Модель', max_length=255)
    year = models.IntegerField(verbose_name='Год выпуска', null=True, blank=True)
    state_number = models.CharField(verbose_name='Гос. номер', max_length=255, unique=True)
    mileage = models.DecimalField(
        verbose_name='Пробег(км)',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Обновляется каждый день в 00:00',
    )
    engine_hours = models.DecimalField(
        verbose_name='Моточасы(ч)',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Обновляется каждый день в 00:00',
    )
    interval_oil_change = models.IntegerField(verbose_name='Интервал замены масла(км)', default=10_000)
    interval_timing_belt_change = models.IntegerField(verbose_name='Интервал замены ремня ГРМ(км)', default=90_000)
    interval_timing_roller_change = models.IntegerField(verbose_name='Интервал замены роликов ГРМ(км)', default=90_000)
    tracker_id = models.PositiveIntegerField(verbose_name='Идентификатор маячка', blank=True, null=True, unique=True)

    class Meta:
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили'
        ordering = ['brand']

    def __str__(self):
        return f'{self.brand} {self.model} {self.state_number}'

    def update_mileage(self, mileage):
        self.mileage = mileage

    def update_engine_hours(self, engine_hours):
        self.engine_hours = engine_hours

    def _is_change_due(self, service_type, interval_attr):
        last_service = self.services.filter(type_of_work=service_type).last()
        if last_service is None:
            return False
        mileage_difference = self.mileage - last_service.mileage
        return interval_attr - 500 <= mileage_difference <= interval_attr or mileage_difference > interval_attr

    def is_oil_change_due(self):
        return self._is_change_due(Service.TypeOfWork.OIL, self.interval_oil_change)

    def is_timing_belt_change_due(self):
        return self._is_change_due(Service.TypeOfWork.TIMING_BELT, self.interval_timing_belt_change)

    def is_timing_roller_change_due(self):
        return self._is_change_due(Service.TypeOfWork.TIMING_ROLLER, self.interval_timing_roller_change)

    def print_notification(self, message):
        logger.info('garage notification preview car_id=%s message=%s', self.id, message, extra={'event': 'garage_notification_preview'})

    def notify_oil_change_due(self):
        self.print_notification(f'Для автомобиля {self.year} {self.brand} {self.model} необходимо заменить масло!')

    def notify_timing_belt_change_due(self):
        self.print_notification(f'Для автомобиля {self.year} {self.brand} {self.model} необходимо заменить ремень ГРМ!')

    def notify_timing_roller_change_due(self):
        self.print_notification(f'Для автомобиля {self.year} {self.brand} {self.model} необходимо заменить ролики ремня ГРМ!')

    def notify_mechanic(self):
        current_mileage = self.mileage
        last_service = Service.objects.filter(car=self).latest('date')
        last_service_mileage = last_service.mileage

        if (current_mileage - last_service_mileage) >= self.interval_oil_change:
            logger.info('garage mechanic notification due type=oil car_id=%s', self.id, extra={'event': 'garage_oil_due'})
        if (current_mileage - last_service_mileage) >= self.interval_timing_belt_change:
            logger.info('garage mechanic notification due type=timing_belt car_id=%s', self.id, extra={'event': 'garage_timing_belt_due'})
        if (current_mileage - last_service_mileage) >= self.interval_timing_roller_change:
            logger.info('garage mechanic notification due type=timing_roller car_id=%s', self.id, extra={'event': 'garage_timing_roller_due'})


class Driver(TimestampMixin):
    name = models.CharField(max_length=50, verbose_name='Имя')
    phone = models.CharField(max_length=50, verbose_name='Телефон')
    car = models.OneToOneField(
        Car,
        related_name='driver',
        on_delete=models.SET_NULL,
        verbose_name='Автомобиль',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Водитель'
        verbose_name_plural = 'Водители'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}'


class Service(TimestampMixin):
    class TypeOfWork(models.IntegerChoices):
        OIL = 0, 'Замена масла ДВС'
        TIMING_BELT = 1, 'Замена ремня ГРМ'
        TIMING_ROLLER = 2, 'Замена ролика ГРМ'

    car = models.ForeignKey(Car, related_name='services', verbose_name='Автомобиль', on_delete=models.CASCADE)
    type_of_work = models.PositiveSmallIntegerField(verbose_name='Тип работ', choices=TypeOfWork.choices, default=TypeOfWork.OIL)
    notes = models.TextField(verbose_name='Примечания', max_length=255, blank=True, null=True)
    date = models.DateField(verbose_name='Дата обслуживания', default=timezone.now)
    mileage = models.DecimalField(verbose_name='Пробег(км)', max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Запись в журнале автомобиля'
        verbose_name_plural = 'Журнал автомобиля'

    def __str__(self):
        return f'{self.date} {self.car} - {self.get_type_of_work_display()}'

    def save(self, *args, **kwargs):
        if not self.mileage:
            self.mileage = self.car.mileage
        super().save(*args, **kwargs)
