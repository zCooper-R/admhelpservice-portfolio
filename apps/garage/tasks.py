from apps.garage import services as garage_services
from config.celery import app


@app.task
def task_update_car_mileage_and_engine_hours(_request_id: str = None):
    garage_services.update_car_mileage_and_engine_hours()


@app.task
def task_notify_mechanic(_request_id: str = None):
    garage_services.notify_mechanic()
