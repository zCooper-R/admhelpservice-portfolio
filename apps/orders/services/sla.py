from datetime import timedelta

from django.utils import timezone

from apps.orders.choices import OrderWaitingFor

EXECUTOR_RESPONSE_TIMEOUT = timedelta(hours=2)
REQUESTER_RESPONSE_TIMEOUT = timedelta(hours=24)
WARNING_THRESHOLD = 0.2

SLA_TIMEOUTS = {
    OrderWaitingFor.EXECUTOR: EXECUTOR_RESPONSE_TIMEOUT,
    OrderWaitingFor.REQUESTER: REQUESTER_RESPONSE_TIMEOUT,
}


def get_response_deadline(order):
    timeout = SLA_TIMEOUTS.get(getattr(order, "waiting_for", None))
    waiting_since = getattr(order, "waiting_since", None)
    if timeout is None or waiting_since is None:
        return None
    return waiting_since + timeout


def get_time_left(order):
    deadline = get_response_deadline(order)
    if deadline is None:
        return None
    return deadline - timezone.now()


def get_sla_state(order):
    deadline = get_response_deadline(order)
    if deadline is None:
        return "ok"

    time_left = deadline - timezone.now()
    if time_left.total_seconds() <= 0:
        return "overdue"

    timeout = SLA_TIMEOUTS.get(getattr(order, "waiting_for", None))
    if timeout and time_left.total_seconds() <= timeout.total_seconds() * WARNING_THRESHOLD:
        return "warning"

    return "ok"
