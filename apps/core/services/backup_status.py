import subprocess
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from django.utils import timezone


DB_NAME = 'helpservice'
DAILY_BACKUP_DIR = Path('/opt/backups/postgres/daily')
WEEKLY_BACKUP_DIR = Path('/opt/backups/postgres/weekly')
BACKUP_LOG_PATH = Path('/var/log/admhelpservice-backup.log')
TIMER_NAME = 'admhelpservice-pg-backup.timer'
DAILY_WARNING_AGE = timedelta(hours=36)
WEEKLY_WARNING_AGE = timedelta(days=8)
LOG_LINE_LIMIT = 50
SYSTEMCTL_TIMEOUT_SECONDS = 3
SECRET_PATTERN = re.compile(r'(?i)\b(password|passwd|secret|token|key)\b(\s*[:=]\s*)(\S+)')


@dataclass(frozen=True)
class BackupFileStatus:
    kind: str
    found: bool
    file_name: str = ''
    path: str = ''
    created_at: Optional[datetime] = None
    size_bytes: int = 0
    size_display: str = ''
    age: Optional[timedelta] = None
    age_display: str = ''
    status: str = 'missing'
    message: str = ''


def _format_size(size_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'B':
                return f'{int(size)} {unit}'
            return f'{size:.1f} {unit}'
        size /= 1024


def _format_age(age):
    if age is None:
        return ''
    total_seconds = max(0, int(age.total_seconds()))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f'{days}d {hours}h'
    if hours:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'


def _latest_backup(directory, kind, warning_age, now=None):
    now = now or timezone.now()
    try:
        candidates = []
        for path in directory.glob(f'{DB_NAME}_*.dump'):
            if path.is_file():
                candidates.append((path.stat().st_mtime, path))
    except OSError as exc:
        return BackupFileStatus(
            kind=kind,
            found=False,
            status='critical',
            message=f'Не удалось прочитать каталог бэкапов: {exc}',
        )

    if not candidates:
        return BackupFileStatus(
            kind=kind,
            found=False,
            status='missing',
            message='Файл бэкапа не найден.',
        )

    latest = max(candidates, key=lambda item: item[0])[1]
    try:
        stat_result = latest.stat()
    except OSError as exc:
        return BackupFileStatus(
            kind=kind,
            found=False,
            status='critical',
            message=f'Не удалось прочитать метаданные файла бэкапа: {exc}',
        )

    if timezone.is_aware(now):
        created_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.get_current_timezone())
    else:
        created_at = datetime.fromtimestamp(stat_result.st_mtime)
    age = now - created_at
    status = 'ok' if age <= warning_age else 'warning'
    message = 'Файл бэкапа актуален.' if status == 'ok' else 'Файл бэкапа старше ожидаемого порога.'

    return BackupFileStatus(
        kind=kind,
        found=True,
        file_name=latest.name,
        path=str(latest),
        created_at=created_at,
        size_bytes=stat_result.st_size,
        size_display=_format_size(stat_result.st_size),
        age=age,
        age_display=_format_age(age),
        status=status,
        message=message,
    )


def _run_systemctl(args):
    try:
        completed = subprocess.run(
            ['systemctl', *args],
            capture_output=True,
            check=False,
            text=True,
            timeout=SYSTEMCTL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return None, 'systemctl недоступен в текущем окружении.'
    except subprocess.TimeoutExpired:
        return None, 'Команда systemctl не ответила за отведённое время.'
    except OSError as exc:
        return None, f'Не удалось выполнить systemctl: {exc}'
    return completed, ''


def _timer_status():
    active_result, active_error = _run_systemctl(['is-active', TIMER_NAME])
    if active_result is None:
        active = 'unknown'
        message = active_error
    else:
        active = (active_result.stdout or '').strip() or 'unknown'
        message = (active_result.stderr or '').strip()

    timers_result, timers_error = _run_systemctl([
        'list-timers',
        TIMER_NAME,
        '--no-pager',
        '--no-legend',
    ])
    raw_line = ''
    next_run = ''
    last_run = ''
    if timers_result is None:
        message = timers_error if not message else f'{message} {timers_error}'
    else:
        raw_line = (timers_result.stdout or '').strip()
        if raw_line:
            parts = raw_line.split()
            if len(parts) >= 11:
                next_run = ' '.join(parts[0:4])
                last_run = ' '.join(parts[6:10]) if parts[6] != 'n/a' else 'n/a'
            else:
                next_run = raw_line

    return {
        'active': active,
        'next_run': next_run,
        'last_run': last_run,
        'raw': raw_line,
        'message': message,
    }


def _tail_log(log_path=BACKUP_LOG_PATH, limit=LOG_LINE_LIMIT):
    try:
        with log_path.open('r', encoding='utf-8', errors='replace') as log_file:
            lines = log_file.readlines()[-limit:]
    except FileNotFoundError:
        return {
            'available': False,
            'message': 'Файл лога бэкапов не найден.',
            'lines': [],
        }
    except OSError as exc:
        return {
            'available': False,
            'message': f'Не удалось прочитать лог бэкапов: {exc}',
            'lines': [],
        }
    return {
        'available': True,
        'message': '',
        'lines': [SECRET_PATTERN.sub(r'\1\2[redacted]', line.rstrip('\n')) for line in lines],
    }


def _health(daily, weekly):
    weekly_warning = ''
    if not weekly.found:
        weekly_warning = 'Weekly-бэкап не найден.'
    elif weekly.age is not None and weekly.age > WEEKLY_WARNING_AGE:
        weekly_warning = 'Weekly-бэкап старше 8 дней.'

    if not daily.found or daily.status == 'critical':
        return {
            'level': 'CRITICAL',
            'message': daily.message or 'Daily-бэкап отсутствует или недоступен для чтения.',
            'weekly_warning': weekly_warning,
        }
    if daily.age is not None and daily.age > DAILY_WARNING_AGE:
        return {
            'level': 'WARNING',
            'message': 'Daily-бэкап старше 36 часов.',
            'weekly_warning': weekly_warning,
        }
    return {
        'level': 'OK',
        'message': 'Daily-бэкап актуален.',
        'weekly_warning': weekly_warning,
    }


def get_backup_status(
    daily_dir=DAILY_BACKUP_DIR,
    weekly_dir=WEEKLY_BACKUP_DIR,
    log_path=BACKUP_LOG_PATH,
    now=None,
):
    now = now or timezone.now()
    daily = _latest_backup(Path(daily_dir), 'daily', DAILY_WARNING_AGE, now=now)
    weekly = _latest_backup(Path(weekly_dir), 'weekly', WEEKLY_WARNING_AGE, now=now)
    return {
        'daily': daily,
        'weekly': weekly,
        'timer': _timer_status(),
        'log': _tail_log(Path(log_path)),
        'health': _health(daily, weekly),
    }
