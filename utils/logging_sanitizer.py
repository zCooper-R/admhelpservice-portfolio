SENSITIVE_KEYS = {
    'password',
    'passwd',
    'token',
    'access_token',
    'refresh_token',
    'secret',
    'api_key',
    'authorization',
    'cookie',
    'sessionid',
}


def mask_value(value):
    if value in (None, ''):
        return value
    text = str(value)
    if len(text) <= 4:
        return '***'
    return f'{text[:2]}***{text[-2:]}'


def sanitize_mapping(payload):
    if not isinstance(payload, dict):
        return payload

    sanitized = {}
    for key, value in payload.items():
        normalized_key = str(key).lower()
        if normalized_key in SENSITIVE_KEYS:
            sanitized[key] = mask_value(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_mapping(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_mapping(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized


def safe_recipient_count(recipients):
    if not recipients:
        return 0
    return len([recipient for recipient in recipients if recipient])
