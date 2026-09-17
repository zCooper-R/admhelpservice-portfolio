import logging

from utils.logging_context import get_log_context


class ContextEnrichmentFilter(logging.Filter):
    def filter(self, record):
        context = get_log_context()
        for key, value in context.items():
            setattr(record, key, value)
        if not hasattr(record, 'status_code'):
            record.status_code = '-'
        if not hasattr(record, 'duration_ms'):
            record.duration_ms = '-'
        if not hasattr(record, 'event'):
            record.event = record.getMessage()
        return True
