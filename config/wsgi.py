"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from settings_loader import resolve_settings_module

os.environ.setdefault("DJANGO_EXECUTION_ENVIRONMENT", "PORTFOLIO")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", resolve_settings_module())

application = get_wsgi_application()
