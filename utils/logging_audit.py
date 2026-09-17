import logging


audit_logger = logging.getLogger('adm.audit')


def log_audit(*, action: str, actor=None, entity=None, entity_id=None, result='success', extra=None):
    username = getattr(actor, 'get_username', lambda: None)() if actor else None
    user_id = getattr(actor, 'pk', None) if actor else None
    payload = {
        'action': action,
        'actor_id': user_id or '-',
        'actor_username': username or 'anonymous',
        'entity': entity or '-',
        'entity_id': entity_id or '-',
        'result': result,
    }
    if extra:
        payload.update(extra)

    audit_logger.info(
        'audit action=%s actor_id=%s actor_username=%s entity=%s entity_id=%s result=%s',
        payload['action'],
        payload['actor_id'],
        payload['actor_username'],
        payload['entity'],
        payload['entity_id'],
        payload['result'],
        extra={'event': 'audit', 'audit': payload},
    )
