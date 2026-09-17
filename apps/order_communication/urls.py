from django.urls import path

from apps.order_communication.views.api import (
    AttachmentDownloadView,
    CreateInternalNoteView,
    CreatePublicReplyView,
    MarkThreadReadView,
    ThreadPollView,
)
from apps.order_communication.views.thread import ThreadFragmentView

app_name = "order_communication"

urlpatterns = [
    path("orders/<int:order_id>/discussion/", ThreadFragmentView.as_view(), name="thread_fragment"),
    path("orders/<int:order_id>/discussion/public-reply/", CreatePublicReplyView.as_view(), name="public_reply_create"),
    path("orders/<int:order_id>/discussion/internal-note/", CreateInternalNoteView.as_view(), name="internal_note_create"),
    path("orders/<int:order_id>/discussion/read/", MarkThreadReadView.as_view(), name="thread_mark_read"),
    path("orders/<int:order_id>/discussion/poll/", ThreadPollView.as_view(), name="thread_poll"),
    path("attachments/<int:attachment_id>/download/", AttachmentDownloadView.as_view(), name="attachment_download"),
]
