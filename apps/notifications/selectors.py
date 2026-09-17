from apps.notifications.models import Notification


def get_notifications_for_user(user):
    return (
        Notification.objects
        .for_user(user)
        .select_related("actor", "recipient")
        .order_by("-created_at", "-id")
    )


def get_recent_notifications_for_user(user, *, limit: int = 6):
    return get_notifications_for_user(user)[:limit]


def get_unread_notifications_for_user(user):
    return get_notifications_for_user(user).unread()


def format_unread_count(count: int) -> str:
    return "99+" if count > 99 else str(count)


def get_unread_count_for_user(user) -> int:
    if not getattr(user, "is_authenticated", False):
        return 0
    return Notification.objects.for_user(user).unread().count()
