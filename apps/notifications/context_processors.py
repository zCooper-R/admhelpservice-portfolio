from apps.notifications.selectors import format_unread_count, get_unread_count_for_user


def notifications_context_processor(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"notifications_unread_count": 0}

    unread_count = get_unread_count_for_user(request.user)
    return {
        "notifications_unread_count": unread_count,
        "notifications_unread_count_display": format_unread_count(unread_count),
    }
