import logging
from typing import List

from django.apps import apps

from apps.orders.services.workflow import get_moderators_for_order

logger = logging.getLogger(__name__)


class ModeratorFromGroups:
    """
    Возвращает Telegram ID workflow-модераторов для конкретного типа заявки.
    Источник правды — группы, явно привязанные к правилу маршрутизации.
    """

    @staticmethod
    def get_tg_ids(category: str) -> List[str]:
        try:
            model = apps.get_model("orders", category)
        except LookupError:
            logger.warning("Не удалось определить модель заявок для категории %s", category)
            return []

        moderators = get_moderators_for_order(model())
        if not moderators.exists():
            logger.warning("Для модели %s не настроены workflow-модераторы", category)
            return []

        tg_ids = []
        for user in moderators.filter(is_active=True, inform_me=True):
            if user.get_tlg():
                tg_ids.append(user.get_tlg())

        if not tg_ids:
            logger.warning("Для модели %s нет активных модераторов с Telegram ID", category)
        return tg_ids
