from apps.order_communication.models import OrderMessageAttachment


def create_attachments(message, files, actor):
    attachments = []
    for file_obj in files or []:
        attachments.append(
            OrderMessageAttachment.objects.create(
                message=message,
                file=file_obj,
                original_name=file_obj.name,
                content_type=getattr(file_obj, "content_type", "") or "",
                size=getattr(file_obj, "size", 0) or 0,
                uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
            )
        )
    return attachments


def get_attachment_download_queryset(user):
    # TODO: add dedicated download view once attachment access rules are finalized.
    return OrderMessageAttachment.objects.select_related("message", "message__thread", "uploaded_by")
