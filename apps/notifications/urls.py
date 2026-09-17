from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("panel/", views.notification_panel, name="panel"),
    path("summary/", views.notification_summary, name="summary"),
    path("<int:notification_id>/open/", views.open_notification, name="open"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("delete-all/", views.delete_all, name="delete_all"),
]
