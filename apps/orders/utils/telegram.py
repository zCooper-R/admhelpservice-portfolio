from apps.users.telegram_messages import new_order_message, new_order_transport_message


def build_order_transport_notification_message(obj, ct):
    pass


def build_notification_message(obj, ct):
    """
    Формирует сообщение для уведомления в телеграм на основе объекта и ContentType.
    """
    category_emoji_dict = {
        "orderprinter": "🖨",
        "ordertransport": "🚕",
        "orderpc": "🖥",
        "orderaho": "🛠️",
        "orderaccount": "🕵",
        "ordervks": "🎥",
    }
    category_emoji = category_emoji_dict.get(ct.model)
    if ct.model == "ordertransport":
        return new_order_transport_message.format(
            category=obj,
            category_emoji=category_emoji,
            id=obj.id,
            client=obj.client,
            phone=obj.phone,
            address=obj.address,
            transport_arrival_datetime=obj.transport_arrival_datetime.strftime("%H:%M %d-%m-%y"),
            comeback="✅" if obj.comeback else "⛔️",
        )

    return new_order_message.format(
        category=obj.get_category_display(),
        category_emoji=category_emoji,
        id=obj.id,
        client=obj.client,
        description=f"🧾 - {obj.description}\n" if obj.description else "",
        address=obj.address,
        cabinet=obj.cabinet,
        phone=obj.phone,
    )
