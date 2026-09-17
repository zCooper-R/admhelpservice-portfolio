from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.formats import date_format
from django.views import View

from apps.order_communication.forms import OrderInternalNoteForm, OrderPublicReplyForm
from apps.order_communication.models import OrderMessageAttachment
from apps.order_communication.selectors.threads import get_thread_for_order_visible_to_user
from apps.order_communication.services.messages import create_internal_note, create_public_message
from apps.order_communication.services.policies import can_download_attachment
from apps.order_communication.services.read_state import get_thread_unread_count, mark_thread_read
from apps.order_communication.views.thread import build_thread_context
from apps.order_communication.views.mixins import AjaxRequestRequiredMixin, MessageFormMixin, OrderCommunicationOrderMixin


class ThreadMessageCreateBaseView(LoginRequiredMixin, AjaxRequestRequiredMixin, OrderCommunicationOrderMixin, MessageFormMixin, View):
    form_class = None

    @staticmethod
    def build_order_summary(order):
        order.refresh_from_db()
        return {
            "id": order.pk,
            "status": (
                getattr(order.content_object, "get_status_display", lambda: "-")()
                if order.content_object is not None
                else "-"
            ),
            "waiting_for": order.get_waiting_for_display(),
        }

    @staticmethod
    def build_thread_summary(context):
        latest_visible_message_at = context.get("latest_visible_message_at")
        return {
            "messages_count": context.get("messages_count", 0),
            "latest_visible_message_at": (
                date_format(latest_visible_message_at, "d.m.Y H:i")
                if latest_visible_message_at is not None
                else ""
            ),
        }

    def get_success_payload(self, order):
        context = build_thread_context(order, self.request.user)
        return {
            "success": True,
            "latest_message_id": context["latest_message_id"],
            "unread_count": context["discussion_unread_count"],
            "order_summary": self.build_order_summary(order),
            "thread_summary": self.build_thread_summary(context),
            "thread_html": render_to_string(
                "order_communication/_thread.html",
                context,
                request=self.request,
            ),
        }

    def form_invalid_response(self, form):
        return JsonResponse({"success": False, "errors": form.errors}, status=400)


class CreatePublicReplyView(ThreadMessageCreateBaseView):
    form_class = OrderPublicReplyForm

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid_response(form)

        create_public_message(
            order,
            author=request.user,
            body=form.cleaned_data["body"],
            files=form.cleaned_data.get("attachments"),
        )
        return JsonResponse(self.get_success_payload(order))


class CreateInternalNoteView(ThreadMessageCreateBaseView):
    form_class = OrderInternalNoteForm

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid_response(form)

        create_internal_note(
            order,
            author=request.user,
            body=form.cleaned_data["body"],
            files=form.cleaned_data.get("attachments"),
        )
        return JsonResponse(self.get_success_payload(order))


class MarkThreadReadView(LoginRequiredMixin, AjaxRequestRequiredMixin, OrderCommunicationOrderMixin, View):
    def post(self, request, *args, **kwargs):
        order = self.get_order()
        thread = get_thread_for_order_visible_to_user(order, request.user)
        if thread is None:
            return JsonResponse({"success": True, "unread_count": 0})

        read_state = mark_thread_read(thread, request.user)
        return JsonResponse(
            {
                "success": True,
                "thread_id": thread.pk,
                "read_state_id": read_state.pk,
                "unread_count": get_thread_unread_count(thread, request.user),
            }
        )


class ThreadPollView(LoginRequiredMixin, AjaxRequestRequiredMixin, OrderCommunicationOrderMixin, View):
    def get(self, request, *args, **kwargs):
        order = self.get_order()
        context = build_thread_context(order, request.user)
        thread = context["thread"]
        return JsonResponse(
            {
                "success": True,
                "has_thread": thread is not None,
                "thread_id": thread.pk if thread is not None else None,
                "latest_message_id": context["latest_message_id"],
                "unread_count": context["discussion_unread_count"],
                "thread_html": render_to_string(
                    "order_communication/_thread.html",
                    context,
                    request=request,
                ),
            }
        )


class AttachmentDownloadView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        attachment = get_object_or_404(
            OrderMessageAttachment.objects.select_related(
                "message",
                "message__thread",
                "message__thread__order",
            ),
            pk=kwargs["attachment_id"],
            is_deleted=False,
        )

        if not can_download_attachment(request.user, attachment):
            raise PermissionDenied

        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name or attachment.file.name.rsplit("/", 1)[-1],
        )
