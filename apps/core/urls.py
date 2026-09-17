from django.urls import path

from apps.core.views.backups import BackupStatusView


app_name = 'core'

urlpatterns = [
    path('backups/', BackupStatusView.as_view(), name='backup_status'),
]
