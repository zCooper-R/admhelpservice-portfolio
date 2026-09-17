from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.core.services import backup_status


pytestmark = pytest.mark.django_db


def _create_backup(path, content=b'backup', mtime=None):
    path.write_bytes(content)
    if mtime is not None:
        timestamp = mtime.timestamp()
        import os

        os.utime(path, (timestamp, timestamp))
    return path


def test_backup_status_reports_daily_ok_and_missing_weekly(tmp_path, monkeypatch):
    now = timezone.now()
    daily_dir = tmp_path / 'daily'
    weekly_dir = tmp_path / 'weekly'
    daily_dir.mkdir()
    weekly_dir.mkdir()
    log_path = tmp_path / 'backup.log'
    log_path.write_text('line 1\nline 2\n', encoding='utf-8')
    _create_backup(daily_dir / 'helpservice_2026-05-21.dump', mtime=now - timedelta(hours=2))
    monkeypatch.setattr(backup_status, '_timer_status', lambda: {'active': 'unknown'})

    status = backup_status.get_backup_status(daily_dir, weekly_dir, log_path, now=now)

    assert status['health']['level'] == 'OK'
    assert status['daily'].found is True
    assert status['weekly'].found is False
    assert status['health']['weekly_warning'] == 'Weekly-бэкап не найден.'
    assert status['log']['lines'] == ['line 1', 'line 2']


def test_backup_status_warns_for_stale_daily_and_weekly(tmp_path, monkeypatch):
    now = timezone.now()
    daily_dir = tmp_path / 'daily'
    weekly_dir = tmp_path / 'weekly'
    daily_dir.mkdir()
    weekly_dir.mkdir()
    _create_backup(daily_dir / 'helpservice_2026-05-19.dump', mtime=now - timedelta(hours=40))
    _create_backup(weekly_dir / 'helpservice_2026-05-10.dump', mtime=now - timedelta(days=9))
    missing_log = tmp_path / 'missing.log'
    monkeypatch.setattr(backup_status, '_timer_status', lambda: {'active': 'unknown'})

    status = backup_status.get_backup_status(daily_dir, weekly_dir, missing_log, now=now)

    assert status['health']['level'] == 'WARNING'
    assert status['health']['message'] == 'Daily-бэкап старше 36 часов.'
    assert status['health']['weekly_warning'] == 'Weekly-бэкап старше 8 дней.'
    assert status['log']['available'] is False


def test_backup_status_critical_when_daily_missing(tmp_path, monkeypatch):
    daily_dir = tmp_path / 'daily'
    weekly_dir = tmp_path / 'weekly'
    daily_dir.mkdir()
    weekly_dir.mkdir()
    monkeypatch.setattr(backup_status, '_timer_status', lambda: {'active': 'unknown'})

    status = backup_status.get_backup_status(daily_dir, weekly_dir, tmp_path / 'missing.log')

    assert status['health']['level'] == 'CRITICAL'
    assert status['daily'].found is False


def test_timer_status_handles_missing_systemctl(monkeypatch):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(backup_status.subprocess, 'run', raise_missing)

    status = backup_status._timer_status()

    assert status['active'] == 'unknown'
    assert 'systemctl недоступен' in status['message']


def test_backup_log_lines_are_redacted(tmp_path):
    log_path = tmp_path / 'backup.log'
    log_path.write_text('ok\npassword=secret-value\ntoken: abc123\n', encoding='utf-8')

    status = backup_status._tail_log(log_path)

    assert status['available'] is True
    assert status['lines'] == ['ok', 'password=[redacted]', 'token: [redacted]']


def test_backup_status_page_requires_staff(client, monkeypatch):
    monkeypatch.setattr(backup_status, 'get_backup_status', lambda: {})
    url = reverse('core:backup_status')
    user_model = get_user_model()
    user = user_model.objects.create_user(username='backup_user', password='password')

    anonymous_response = client.get(url)
    assert anonymous_response.status_code == 302

    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 403


def test_backup_status_page_allows_staff(client, monkeypatch):
    monkeypatch.setattr(
        'apps.core.views.backups.get_backup_status',
        lambda: {
            'health': {'level': 'OK', 'message': 'Daily-бэкап актуален.', 'weekly_warning': ''},
            'daily': backup_status.BackupFileStatus(kind='daily', found=False, status='missing'),
            'weekly': backup_status.BackupFileStatus(kind='weekly', found=False, status='missing'),
            'timer': {'active': 'unknown', 'next_run': '', 'last_run': '', 'raw': '', 'message': ''},
            'log': {'available': False, 'message': 'Не удалось прочитать лог бэкапов.', 'lines': []},
        },
    )
    user_model = get_user_model()
    staff = user_model.objects.create_user(username='backup_staff', password='password', is_staff=True)

    client.force_login(staff)
    response = client.get(reverse('core:backup_status'))

    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Статус PostgreSQL-бэкапов' in content
    assert 'Не удалось прочитать лог бэкапов.' in content
