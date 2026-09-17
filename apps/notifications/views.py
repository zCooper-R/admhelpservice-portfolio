from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.notifications.models import Notification
from apps.notifications.selectors import (
    format_unread_count,
    get_notifications_for_user,
    get_recent_notifications_for_user,
    get_unread_count_for_user,
)
from apps.notifications.services import (
    delete_all_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _summary_payload(user) -> dict:
    unread_count = get_unread_count_for_user(user)
    return {
        "unread_count": unread_count,
        "unread_count_display": format_unread_count(unread_count),
    }


def get_notification_summary_payload(user) -> dict:
    return _summary_payload(user)


@login_required
def notification_list(request):
    paginator = Paginator(get_notifications_for_user(request.user), 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "notifications": page_obj.object_list,
        **_summary_payload(request.user),
    }
    if request.GET.get("fragment") == "list":
        return render(request, "notifications/_list.html", context)
    return render(request, "notifications/list.html", context)


@login_required
def notification_panel(request):
    return render(
        request,
        "notifications/_panel.html",
        {
            "notifications": get_recent_notifications_for_user(request.user),
            "list_url": reverse("notifications:list"),
            **_summary_payload(request.user),
        },
    )


@login_required
def notification_summary(request):
    return JsonResponse(_summary_payload(request.user))


@login_required
def open_notification(request, notification_id):
    notification = get_object_or_404(Notification.objects.for_user(request.user), pk=notification_id)
    mark_notification_as_read(notification)
    return redirect(notification.get_target_url())


@login_required
@require_POST
def mark_all_read(request):
    updated = mark_all_notifications_as_read(request.user)
    if _is_ajax(request):
        return JsonResponse({"updated": updated, **_summary_payload(request.user)})
    if updated:
        messages.success(request, "Все уведомления отмечены как прочитанные.")
    else:
        messages.info(request, "Непрочитанных уведомлений нет.")
    return redirect("notifications:list")


@login_required
@require_POST
def delete_all(request):
    deleted = delete_all_notifications(request.user)
    if _is_ajax(request):
        return JsonResponse({"deleted": deleted, **_summary_payload(request.user)})
    if deleted:
        messages.success(request, "История уведомлений очищена.")
    else:
        messages.info(request, "Удалять нечего.")
    return redirect("notifications:list")
