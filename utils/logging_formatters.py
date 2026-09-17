import json
import logging
from datetime import datetime


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno,
            'request_id': getattr(record, 'request_id', '-'),
            'user_id': getattr(record, 'user_id', '-'),
            'username': getattr(record, 'username', 'anonymous'),
            'remote_addr': getattr(record, 'remote_addr', '-'),
            'method': getattr(record, 'method', '-'),
            'path': getattr(record, 'path', '-'),
            'status_code': getattr(record, 'status_code', '-'),
            'duration_ms': getattr(record, 'duration_ms', '-'),
            'celery_task_id': getattr(record, 'celery_task_id', '-'),
        }
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
