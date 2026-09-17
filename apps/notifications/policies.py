from typing import List, NamedTuple, Optional

from apps.orders.services.workflow import get_moderators_for_order


REQUESTER_AUDIENCE = "requester"
SPECIALIST_AUDIENCE = "specialist"
MODERATOR_AUDIENCE = "moderator"


class NotificationRoute(NamedTuple):
    recipient: object
    audience: str


class AssignmentNotificationRoutes(NamedTuple):
    requester: Optional[NotificationRoute]
    previous_specialist: Optional[NotificationRoute]
    current_specialist: Optional[NotificationRoute]


class OrderNotificationParticipants(NamedTuple):
    owner: Optional[object]
    specialist: Optional[object]
    actor: Optional[object]

    @property
    def actor_is_owner(self) -> bool:
        return self.actor is not None and self.actor == self.owner

    @property
    def actor_is_specialist(self) -> bool:
        return self.actor is not None and self.actor == self.specialist


def get_order_notification_participants(order_object, actor=None) -> OrderNotificationParticipants:
    specialist = getattr(order_object, "support_specialist", None)
    specialist_user = getattr(specialist, "user", None) if specialist else None
    return OrderNotificationParticipants(
        owner=getattr(order_object, "owner", None),
        specialist=specialist_user,
        actor=actor,
    )


def get_moderator_routes(order_object, actor=None) -> List[NotificationRoute]:
    participants = get_order_notification_participants(order_object, actor=actor)
    routes = []
    for moderator in get_moderators_for_order(order_object):
        if moderator == participants.actor:
            continue
        if moderator == participants.specialist:
            continue
        routes.append(NotificationRoute(recipient=moderator, audience=MODERATOR_AUDIENCE))
    return routes


def get_creation_routes(order_object, actor=None) -> List[NotificationRoute]:
    participants = get_order_notification_participants(order_object, actor=actor)
    routes = get_moderator_routes(order_object, actor=actor)
    if participants.specialist and participants.specialist != participants.actor:
        routes.append(NotificationRoute(recipient=participants.specialist, audience=SPECIALIST_AUDIENCE))
    return routes


def get_change_routes(order_object, actor=None) -> List[NotificationRoute]:
    participants = get_order_notification_participants(order_object, actor=actor)
    routes = []

    if participants.actor_is_specialist:
        if participants.owner and participants.owner != participants.actor:
            routes.append(NotificationRoute(recipient=participants.owner, audience=REQUESTER_AUDIENCE))
        return routes

    if participants.actor_is_owner:
        if participants.specialist and participants.specialist != participants.actor:
            routes.append(NotificationRoute(recipient=participants.specialist, audience=SPECIALIST_AUDIENCE))
        else:
            routes.extend(get_moderator_routes(order_object, actor=actor))
        return routes

    if participants.owner and participants.owner != participants.actor:
        routes.append(NotificationRoute(recipient=participants.owner, audience=REQUESTER_AUDIENCE))
    if participants.specialist and participants.specialist != participants.actor:
        routes.append(NotificationRoute(recipient=participants.specialist, audience=SPECIALIST_AUDIENCE))
    return routes


def get_assignment_routes(order_object, *, actor=None, old_specialist=None, new_specialist=None) -> AssignmentNotificationRoutes:
    participants = get_order_notification_participants(order_object, actor=actor)
    previous_user = getattr(old_specialist, "user", None) if old_specialist else None
    current_user = getattr(new_specialist, "user", None) if new_specialist else None

    requester_route = None
    if participants.owner and participants.owner != participants.actor:
        requester_route = NotificationRoute(recipient=participants.owner, audience=REQUESTER_AUDIENCE)

    previous_specialist_route = None
    if previous_user and previous_user != participants.actor and previous_user != current_user:
        previous_specialist_route = NotificationRoute(recipient=previous_user, audience=SPECIALIST_AUDIENCE)

    current_specialist_route = None
    if current_user and current_user != participants.actor:
        current_specialist_route = NotificationRoute(recipient=current_user, audience=SPECIALIST_AUDIENCE)

    return AssignmentNotificationRoutes(
        requester=requester_route,
        previous_specialist=previous_specialist_route,
        current_specialist=current_specialist_route,
    )
