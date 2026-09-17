from utils.logging_audit import log_audit


def log_thread_created(*, actor, thread):
    log_audit(
        action="order_thread.create",
        actor=actor,
        entity="order_communication.orderthread",
        entity_id=thread.pk,
        extra={"order_id": thread.order_id},
    )


def log_message_action(*, action, actor, message):
    log_audit(
        action=action,
        actor=actor,
        entity="order_communication.ordermessage",
        entity_id=message.pk,
        extra={
            "order_id": message.thread.order_id,
            "thread_id": message.thread_id,
            "message_type": message.message_type,
            "visibility": message.visibility,
        },
    )


def log_thread_read(*, actor, thread, read_state):
    log_audit(
        action="order_thread.read",
        actor=actor,
        entity="order_communication.orderthreadreadstate",
        entity_id=read_state.pk,
        extra={"order_id": thread.order_id, "thread_id": thread.pk},
    )
