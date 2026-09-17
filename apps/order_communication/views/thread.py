from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from apps.order_communication.forms import OrderInternalNoteForm, OrderPublicReplyForm
from apps.order_communication.selectors.messages import get_visible_messages_for_thread
from apps.order_communication.selectors.threads import get_thread_for_order_visible_to_user
from apps.order_communication.services.policies import can_post_internal_note
from apps.order_communication.services.read_state import get_first_unread_message_id, get_thread_unread_count
from apps.order_communication.views.mixins import OrderCommunicationOrderMixin


class ThreadFragmentView(LoginRequiredMixin, OrderCommunicationOrderMixin, View):
    template_name = "order_communication/_thread.html"

    def get(self, request, *args, **kwargs):
        order = self.get_order()
        return render(request, self.template_name, build_thread_context(order, request.user))


def build_thread_context(order, user):
    thread = get_thread_for_order_visible_to_user(order, user)
    messages = get_visible_messages_for_thread(thread, user) if thread is not None else []
    latest_message_id = messages.values_list("id", flat=True).last() if thread is not None else None
    latest_visible_message = messages.last() if thread is not None else None
    unread_count = get_thread_unread_count(thread, user) if thread is not None else 0
    first_unread_message_id = get_first_unread_message_id(thread, user) if thread is not None else None
    return {
        "order": order,
        "thread": thread,
        "messages": messages,
        "messages_count": messages.count() if thread is not None else 0,
        "latest_message_id": latest_message_id,
        "latest_visible_message_at": latest_visible_message.created_at if latest_visible_message is not None else None,
        "discussion_unread_count": unread_count,
        "first_unread_message_id": first_unread_message_id,
        "public_form": OrderPublicReplyForm(),
        "internal_form": OrderInternalNoteForm(),
        "can_post_internal_note": can_post_internal_note(user, order),
        "public_reply_url": reverse("order_communication:public_reply_create", kwargs={"order_id": order.pk}),
        "internal_note_url": reverse("order_communication:internal_note_create", kwargs={"order_id": order.pk}),
        "mark_read_url": reverse("order_communication:thread_mark_read", kwargs={"order_id": order.pk}),
    }
