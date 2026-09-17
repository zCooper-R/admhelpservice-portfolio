from django.conf.urls.static import static
from django.contrib import admin

from django.conf import settings
from django.urls import path, include

from apps.orders.views.help import HelpPageView
from apps.orders.views.index import IndexPageView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-tools/', include('apps.core.urls')),
    path('', IndexPageView.as_view(), name='index'),
    path('orders/', include('apps.orders.urls')),
    path('surveys/', include('apps.surveys.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('communication/', include('apps.order_communication.urls')),
    path('auth/', include('apps.users.urls')),
    path('help/', HelpPageView.as_view(), name='help'),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = settings.SITE_NAME
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = 'Административная панель'
