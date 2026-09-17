import csv

from django.contrib import admin
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.garage import models


class ExportCsvMixin:
    """
    A mixin to add an "Export to CSV" button to the admin site.
    """

    def export_to_csv(self, request, queryset):
        """
        Export the selected objects to a CSV file.
        """
        model = queryset.model
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model._meta}.csv"'

        writer = csv.writer(response)
        # Write the header row
        writer.writerow([field.verbose_name for field in queryset.model._meta.fields])
        # Write the data rows
        for obj in queryset:
            row = []
            for field in queryset.model._meta.fields:
                if field.choices:
                    value = dict(field.choices).get(getattr(obj, field.name), None)
                    row.append(value)
                else:
                    row.append(getattr(obj, field.name))
            writer.writerow(row)
        return response
    export_to_csv.short_description = "Export to CSV"


class ServiceStackedInLine(admin.StackedInline):
    model = models.Service


class DriverStackedInLine(admin.TabularInline):
    model = models.Driver
    extra = 1


@admin.register(models.Driver)
class DriverAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ['export_to_csv', ]
    list_display = ['id', 'name', 'car_link', ]
    list_display_links = ('id', 'name',)
    search_fields = ['name', 'car__brand', 'car__model']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('car',)
        return queryset

    def car_link(self, driver):
        """
        Создаёт линк на автомобиль
        """
        if driver.car is None:
            return
        url = reverse("admin:garage_car_change", args=(driver.pk,))
        return format_html(f'<a href="{url}">{driver.car}</a>')
    car_link.short_description = "Автомобиль"


@admin.register(models.Car)
class CarAdmin(admin.ModelAdmin, ExportCsvMixin):
    """
    Модель транспорта в панели администрирования
    """

    actions = [
        'export_to_csv',
    ]
    inlines = [
        DriverStackedInLine,
    ]
    search_fields = (
        'brand',
        'model',
        'year',
        'state_number',
        'driver__name',
    )
    list_display_links = (
        'id',
        'brand',
        'model',
    )
    list_display = (
        'id',
        'brand',
        'model',
        'state_number',
        'mileage',
        'driver_link',
    )
    list_filter = ('brand',)
    fieldsets = (
        (
            'Основная информация',
            {
                "fields": (
                    'brand',
                    'model',
                    'year',
                    'state_number',
                )
            }
        ),
        (
            'GPS AvtoControl',
            {
                "fields": (
                    "tracker_id",
                    (
                        'mileage',
                        "engine_hours",
                    )
                ),
            },
        ),
        (
            'Прочее',
            {
                "fields": (
                    'interval_oil_change',
                    "interval_timing_belt_change",
                    "interval_timing_roller_change",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('driver',)
        return queryset

    def driver_link(self, obj):
        """
        Создаёт линк на Водителя
        """
        driver = obj.driver
        if driver is None:
            return
        url = reverse("admin:garage_driver_change", args=(driver.pk,))
        return format_html(mark_safe(f'<a href="{url}">{driver.name}</a>'))

    driver_link.short_description = 'Водитель'


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin, ExportCsvMixin):

    actions = ['export_to_csv', ]
    list_display = (
        'id',
        'car',
        'type_of_work',
        'mileage',
        'date',
    )
    list_filter = (
        'date',
        'car',
        'type_of_work',
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    'date',
                    ('car', 'type_of_work',),
                    'mileage'
                )
            }
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    'notes',


                ),
            },
        ),
    )
